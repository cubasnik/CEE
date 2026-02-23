#!/usr/bin/env python3
"""CEE Hypervisor Manager - Main entry point"""
import argparse
import logging
import sys
import uuid
import time
import os
import subprocess
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные
GLOBAL_ARGS = None

class MockDriver:
    """Mock driver for testing without real virtualization"""
    
    def __init__(self):
        self.vms = {}
        logger.info("Mock driver initialized")
    
    def connect(self):
        return True
    
    def list_vms(self):
        return list(self.vms.values())
    
    def create_vm(self, name, vcpus, memory, image, os_type='linux', storage_gb=20, autostart=False):
        vm_id = str(uuid.uuid4())[:8]
        self.vms[vm_id] = {
            'id': vm_id,
            'name': name,
            'vcpus': int(vcpus),
            'memory_mb': int(memory),
            'memory_gb': round(int(memory)/1024, 1),
            'image': image,
            'os_type': os_type,
            'storage_gb': storage_gb,
            'state': 'running' if autostart else 'stopped',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        logger.info(f"Mock VM created: {name} (ID: {vm_id}, autostart: {autostart})")
        return vm_id
    
    def get_vm(self, vm_id):
        return self.vms.get(vm_id)
    
    def delete_vm(self, vm_id):
        if vm_id in self.vms:
            del self.vms[vm_id]
            logger.info(f"Mock VM {vm_id} deleted")
            return True
        return False
    
    def stop_vm(self, vm_id):
        if vm_id in self.vms:
            self.vms[vm_id]['state'] = 'stopped'
            logger.info(f"Mock VM {vm_id} stopped")
            return True
        return False
    
    def start_vm(self, vm_id):
        if vm_id in self.vms:
            self.vms[vm_id]['state'] = 'running'
            logger.info(f"Mock VM {vm_id} started")
            return True
        return False

class KVMDriver:
    """Real KVM driver using libvirt"""
    
    def __init__(self, uri="qemu:///system"):
        self.uri = uri
        self.conn = None
        self.vm_cache = {}  # Cache for mapping short IDs to full UUIDs
        logger.info(f"KVM driver initialized with URI: {uri}")
    
    def connect(self):
        """Connect to libvirt"""
        try:
            import libvirt
            self.conn = libvirt.open(self.uri)
            if self.conn is None:
                logger.error(f"Failed to connect to {self.uri}")
                return False
            logger.info(f"Connected to libvirt: {self.uri}")
            self._update_cache()
            return True
        except ImportError:
            logger.error("libvirt module not installed. Please install python3-libvirt")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def _update_cache(self):
        """Update the VM cache with current domains"""
        self.vm_cache = {}
        try:
            if not self.conn:
                return
            
            domains = self.conn.listAllDomains(0)
            for domain in domains:
                full_uuid = domain.UUIDString()
                short_id = full_uuid[:8]
                self.vm_cache[short_id] = {
                    'full_uuid': full_uuid,
                    'name': domain.name(),
                    'domain': domain
                }
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
    
    def _get_domain(self, vm_id):
        """Get domain by short ID or name"""
        try:
            import libvirt
            
            # First try cache
            if vm_id in self.vm_cache:
                try:
                    return self.conn.lookupByUUIDString(self.vm_cache[vm_id]['full_uuid'])
                except:
                    pass
            
            # Try as UUID
            try:
                if len(vm_id) == 8:
                    # Try to find by prefix
                    domains = self.conn.listAllDomains(0)
                    for domain in domains:
                        if domain.UUIDString().startswith(vm_id):
                            return domain
                else:
                    return self.conn.lookupByUUIDString(vm_id)
            except:
                pass
            
            # Try as name
            try:
                return self.conn.lookupByName(vm_id)
            except:
                pass
            
            return None
        except Exception as e:
            logger.error(f"Error getting domain {vm_id}: {e}")
            return None
    
    def list_vms(self):
        """List all VMs"""
        vms = []
        try:
            if not self.conn:
                logger.warning("No libvirt connection")
                return vms
            
            domains = self.conn.listAllDomains(0)
            logger.info(f"Found {len(domains)} domains")
            
            self.vm_cache = {}  # Reset cache
            
            for domain in domains:
                try:
                    state, max_mem, memory, vcpus, cpu_time = domain.info()
                    
                    if state == 1:  # VIR_DOMAIN_RUNNING
                        vm_state = 'running'
                    else:
                        vm_state = 'stopped'
                    
                    full_uuid = domain.UUIDString()
                    short_id = full_uuid[:8]
                    
                    # Update cache
                    self.vm_cache[short_id] = {
                        'full_uuid': full_uuid,
                        'name': domain.name(),
                        'domain': domain
                    }
                    
                    vms.append({
                        'id': short_id,
                        'name': domain.name(),
                        'vcpus': vcpus,
                        'memory_mb': memory // 1024,
                        'memory_gb': round(memory / 1024 / 1024, 1),
                        'state': vm_state,
                        'os_type': 'linux',
                        'image': 'unknown'
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing domain {domain.name()}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error listing VMs: {e}")
        
        return vms
    
    def create_vm(self, name, vcpus, memory, image, os_type='linux', storage_gb=20, autostart=False):
        """Create a new VM"""
        try:
            if not self.conn:
                if not self.connect():
                    return None
            
            import libvirt
            
            # Check if VM already exists
            try:
                existing = self.conn.lookupByName(name)
                if existing:
                    logger.error(f"VM with name {name} already exists")
                    return None
            except libvirt.libvirtError:
                pass
            
            # XML configuration for the VM
            xml_config = f"""
            <domain type='kvm'>
                <name>{name}</name>
                <memory unit='MiB'>{memory}</memory>
                <currentMemory unit='MiB'>{memory}</currentMemory>
                <vcpu placement='static'>{vcpus}</vcpu>
                <os>
                    <type arch='x86_64' machine='pc'>hvm</type>
                    <boot dev='hd'/>
                </os>
                <features>
                    <acpi/>
                    <apic/>
                </features>
                <cpu mode='host-passthrough'/>
                <devices>
                    <disk type='file' device='disk'>
                        <driver name='qemu' type='qcow2'/>
                        <source file='{image}'/>
                        <target dev='vda' bus='virtio'/>
                    </disk>
                    <interface type='network'>
                        <source network='default'/>
                        <model type='virtio'/>
                    </interface>
                    <console type='pty'/>
                </devices>
            </domain>
            """
            
            domain = self.conn.defineXML(xml_config)
            if domain is None:
                logger.error(f"Failed to define VM {name}")
                return None
            
            full_uuid = domain.UUIDString()
            short_id = full_uuid[:8]
            
            if autostart:
                domain.create()
                logger.info(f"VM {name} started automatically")
            
            logger.info(f"VM {name} created with ID {short_id}")
            return short_id
            
        except ImportError:
            logger.error("libvirt module not installed")
            return None
        except Exception as e:
            logger.error(f"Error creating VM: {e}")
            return None
    
    def get_vm(self, vm_id):
        """Get VM details by ID"""
        try:
            domain = self._get_domain(vm_id)
            if not domain:
                return None
            
            state, max_mem, memory, vcpus, cpu_time = domain.info()
            
            if state == 1:
                vm_state = 'running'
            else:
                vm_state = 'stopped'
            
            full_uuid = domain.UUIDString()
            short_id = full_uuid[:8]
            
            return {
                'id': short_id,
                'name': domain.name(),
                'vcpus': vcpus,
                'memory_mb': memory // 1024,
                'memory_gb': round(memory / 1024 / 1024, 1),
                'state': vm_state,
                'os_type': 'linux',
                'image': 'unknown'
            }
            
        except Exception as e:
            logger.error(f"Error getting VM {vm_id}: {e}")
            return None
    
    def delete_vm(self, vm_id):
        """Delete a VM"""
        try:
            domain = self._get_domain(vm_id)
            if not domain:
                return False
            
            if domain.isActive():
                domain.destroy()
            domain.undefine()
            logger.info(f"VM {vm_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting VM: {e}")
        return False
    
    def stop_vm(self, vm_id):
        """Stop a VM"""
        try:
            domain = self._get_domain(vm_id)
            if not domain:
                return False
            
            if domain.isActive():
                domain.shutdown()
                logger.info(f"VM {vm_id} stopped")
                return True
        except Exception as e:
            logger.error(f"Error stopping VM: {e}")
        return False
    
    def start_vm(self, vm_id):
        """Start a VM"""
        try:
            domain = self._get_domain(vm_id)
            if not domain:
                return False
            
            if not domain.isActive():
                domain.create()
                logger.info(f"VM {vm_id} started")
                return True
        except Exception as e:
            logger.error(f"Error starting VM: {e}")
        return False

def create_app(driver, driver_name):
    """Create Flask application"""
    app = Flask(__name__, static_folder='static', static_url_path='')
    CORS(app)
    
    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')
    
    @app.route('/api/status')
    def status():
        return jsonify({'status': 'ok', 'driver': driver_name})
    
    @app.route('/api/v1/vms', methods=['GET'])
    def list_vms():
        try:
            vms = driver.list_vms()
            return jsonify(vms)
        except Exception as e:
            logger.error(f"Error in list_vms: {e}")
            return jsonify([])
    
    @app.route('/api/v1/vms', methods=['POST'])
    def create_vm():
        data = request.json
        logger.info(f"Received data: {data}")
        
        required_fields = ['name', 'vcpus', 'memory', 'image']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        try:
            autostart = data.get('autostart', False)
            
            vm_id = driver.create_vm(
                name=data['name'],
                vcpus=int(data['vcpus']),
                memory=int(data['memory']),
                image=data['image'],
                os_type=data.get('os_type', 'linux'),
                storage_gb=int(data.get('storage_gb', 20)),
                autostart=autostart
            )
            
            if vm_id:
                return jsonify({'id': vm_id, 'status': 'created'}), 201
            else:
                return jsonify({'error': 'Failed to create VM'}), 400
                
        except Exception as e:
            logger.error(f"Error creating VM: {e}")
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/v1/vms/<vm_id>', methods=['DELETE'])
    def delete_vm(vm_id):
        if driver.delete_vm(vm_id):
            return jsonify({'status': 'deleted'})
        return jsonify({'error': 'not found'}), 404
    
    @app.route('/api/v1/vms/<vm_id>/stop', methods=['POST'])
    def stop_vm(vm_id):
        if driver.stop_vm(vm_id):
            return jsonify({'status': 'stopped'})
        return jsonify({'error': 'not found'}), 404
    
    @app.route('/api/v1/vms/<vm_id>/start', methods=['POST'])
    def start_vm(vm_id):
        if driver.start_vm(vm_id):
            return jsonify({'status': 'started'})
        return jsonify({'error': 'not found'}), 404
    
    @app.route('/api/images', methods=['GET'])
    def list_images():
        """Список загруженных образов"""
        images_dir = '/var/lib/libvirt/images'
        images = []
        
        try:
            if not os.path.exists(images_dir):
                return jsonify([])
                
            for file in os.listdir(images_dir):
                if file.endswith(('.iso', '.qcow2')):
                    file_path = os.path.join(images_dir, file)
                    size = os.path.getsize(file_path)
                    size_str = f"{size / (1024*1024):.1f} MB" if size < 1024*1024*1024 else f"{size / (1024*1024*1024):.1f} GB"
                    images.append({
                        'name': file,
                        'size': size_str,
                        'type': 'iso' if file.endswith('.iso') else 'qcow2',
                        'path': file_path
                    })
        except PermissionError:
            logger.error("Permission denied accessing images directory")
            return jsonify({'error': 'Permission denied'}), 403
        except Exception as e:
            logger.error(f"Error listing images: {e}")
        
        return jsonify(images)
    
    @app.route('/api/upload-image', methods=['POST'])
    def upload_image():
        """Загрузка образа"""
        if 'image' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        filename = file.filename
        if not filename.lower().endswith(('.iso', '.qcow2')):
            return jsonify({'error': 'Only ISO and QCOW2 files are allowed'}), 400
        
        try:
            filepath = os.path.join('/var/lib/libvirt/images', filename)
            file.save(filepath)
            
            # Установка прав
            subprocess.run(['sudo', 'chown', 'root:libvirt', filepath], check=False)
            subprocess.run(['sudo', 'chmod', '644', filepath], check=False)
            
            logger.info(f"Image uploaded: {filename}")
            return jsonify({'status': 'success', 'filename': filename})
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/images/<filename>', methods=['DELETE'])
    def delete_image(filename):
        """Удаление образа"""
        try:
            filepath = os.path.join('/var/lib/libvirt/images', filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Image deleted: {filename}")
                return jsonify({'status': 'deleted'})
            return jsonify({'error': 'File not found'}), 404
        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/clone-image', methods=['POST'])
    def clone_image():
        """Клонирование образа"""
        data = request.json
        source = data.get('source')
        target = data.get('target')
        
        if not source or not target:
            return jsonify({'error': 'Source and target required'}), 400
        
        try:
            source_path = os.path.join('/var/lib/libvirt/images', source)
            target_path = os.path.join('/var/lib/libvirt/images', target)
            
            if not os.path.exists(source_path):
                return jsonify({'error': 'Source image not found'}), 404
            
            if os.path.exists(target_path):
                return jsonify({'error': 'Target image already exists'}), 400
            
            # Клонирование через qemu-img create -b (создание снапшота)
            cmd = ['sudo', 'qemu-img', 'create', '-f', 'qcow2', '-b', source_path, '-F', 'qcow2', target_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Clone error: {result.stderr}")
                return jsonify({'error': 'Failed to clone image'}), 500
            
            # Установка прав
            subprocess.run(['sudo', 'chown', 'root:libvirt', target_path], check=False)
            subprocess.run(['sudo', 'chmod', '644', target_path], check=False)
            
            logger.info(f"Image cloned: {source} -> {target}")
            return jsonify({'status': 'success', 'target': target})
            
        except Exception as e:
            logger.error(f"Error cloning image: {e}")
            return jsonify({'error': str(e)}), 500
    
    return app

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='CEE Hypervisor Manager')
    parser.add_argument('--driver', choices=['mock', 'kvm'], default='mock',
                       help='Driver to use: mock or kvm')
    parser.add_argument('--uri', default='qemu:///system',
                       help='libvirt URI for KVM driver')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port to run the server on')
    
    if len(sys.argv) > 1:
        return parser.parse_args()
    else:
        return argparse.Namespace(
            driver=os.environ.get('CEE_DRIVER', 'mock'),
            uri=os.environ.get('CEE_URI', 'qemu:///system'),
            port=int(os.environ.get('CEE_PORT', '8000'))
        )

def main():
    """Main entry point"""
    global GLOBAL_ARGS
    GLOBAL_ARGS = parse_arguments()
    
    # Save arguments to environment variables for child processes
    os.environ['CEE_DRIVER'] = GLOBAL_ARGS.driver
    os.environ['CEE_URI'] = GLOBAL_ARGS.uri
    os.environ['CEE_PORT'] = str(GLOBAL_ARGS.port)
    
    # Initialize driver
    if GLOBAL_ARGS.driver == 'kvm':
        logger.info(f"Initializing KVM driver with URI: {GLOBAL_ARGS.uri}")
        driver = KVMDriver(uri=GLOBAL_ARGS.uri)
    else:
        logger.info("Initializing Mock driver")
        driver = MockDriver()
    
    # Connect driver
    if not driver.connect():
        logger.error("Failed to connect driver, exiting")
        sys.exit(1)
    
    # Create and run Flask app
    app = create_app(driver, GLOBAL_ARGS.driver)
    logger.info(f"Starting server on port {GLOBAL_ARGS.port}")
    app.run(host='0.0.0.0', port=GLOBAL_ARGS.port, debug=False)

if __name__ == '__main__':
    main()
