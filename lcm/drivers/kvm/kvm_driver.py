"""KVM/libvirt driver implementation."""
import libvirt
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class KVMDriver:
    """Driver for managing VMs using KVM/libvirt."""
    
    def __init__(self, connection_uri: str = "qemu:///system"):
        """Initialize KVM driver.
        
        Args:
            connection_uri: libvirt connection URI (default: qemu:///system)
        """
        self.connection_uri = connection_uri
        self.conn = None
        
    def connect(self) -> bool:
        """Establish connection to libvirt.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.conn = libvirt.open(self.connection_uri)
            if self.conn is None:
                logger.error(f"Failed to open connection to {self.connection_uri}")
                return False
            logger.info(f"Connected to libvirt: {self.connection_uri}")
            return True
        except libvirt.libvirtError as e:
            logger.error(f"Libvirt connection error: {e}")
            return False
            
    def disconnect(self):
        """Close libvirt connection."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from libvirt")
            
    def create_vm(self, name: str, vcpus: int, memory_mb: int, image_path: str) -> Optional[str]:
        """Create a new virtual machine.
        
        Args:
            name: VM name
            vcpus: Number of virtual CPUs
            memory_mb: Memory in MB
            image_path: Path to disk image
            
        Returns:
            Optional[str]: VM UUID if successful, None otherwise
        """
        if not self.conn:
            if not self.connect():
                return None
                
        try:
            # Basic VM XML template
            xml_config = f"""
            <domain type='kvm'>
                <name>{name}</name>
                <memory unit='MiB'>{memory_mb}</memory>
                <vcpu placement='static'>{vcpus}</vcpu>
                <os>
                    <type arch='x86_64' machine='pc'>hvm</type>
                    <boot dev='hd'/>
                </os>
                <features>
                    <acpi/>
                    <apic/>
                </features>
                <devices>
                    <disk type='file' device='disk'>
                        <driver name='qemu' type='qcow2'/>
                        <source file='{image_path}'/>
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
            
            # Define and start the domain
            domain = self.conn.defineXML(xml_config)
            if domain is None:
                logger.error(f"Failed to define VM {name}")
                return None
                
            domain.create()
            logger.info(f"VM {name} created successfully with UUID: {domain.UUIDString()}")
            return domain.UUIDString()
            
        except libvirt.libvirtError as e:
            logger.error(f"Failed to create VM {name}: {e}")
            return None
            
    def start_vm(self, vm_id: str) -> bool:
        """Start a stopped VM.
        
        Args:
            vm_id: VM UUID or name
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.conn:
            if not self.connect():
                return False
                
        try:
            domain = self.conn.lookupByName(vm_id)
            if domain.isActive():
                logger.info(f"VM {vm_id} is already running")
                return True
                
            domain.create()
            logger.info(f"VM {vm_id} started successfully")
            return True
            
        except libvirt.libvirtError as e:
            logger.error(f"Failed to start VM {vm_id}: {e}")
            return False
            
    def stop_vm(self, vm_id: str, force: bool = False) -> bool:
        """Stop a running VM.
        
        Args:
            vm_id: VM UUID or name
            force: If True, force shutdown
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.conn:
            if not self.connect():
                return False
                
        try:
            domain = self.conn.lookupByName(vm_id)
            if not domain.isActive():
                logger.info(f"VM {vm_id} is already stopped")
                return True
                
            if force:
                domain.destroy()  # Force power off
            else:
                domain.shutdown()  # Graceful shutdown
                
            logger.info(f"VM {vm_id} stopped successfully")
            return True
            
        except libvirt.libvirtError as e:
            logger.error(f"Failed to stop VM {vm_id}: {e}")
            return False
            
    def delete_vm(self, vm_id: str) -> bool:
        """Delete a VM.
        
        Args:
            vm_id: VM UUID or name
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.conn:
            if not self.connect():
                return False
                
        try:
            domain = self.conn.lookupByName(vm_id)
            if domain.isActive():
                domain.destroy()  # Force stop if running
            domain.undefine()  # Remove definition
            logger.info(f"VM {vm_id} deleted successfully")
            return True
            
        except libvirt.libvirtError as e:
            logger.error(f"Failed to delete VM {vm_id}: {e}")
            return False
            
    def list_vms(self) -> list:
        """List all VMs.
        
        Returns:
            list: List of VM information dictionaries
        """
        if not self.conn:
            if not self.connect():
                return []
                
        vms = []
        try:
            for domain_id in self.conn.listDomainsID():
                domain = self.conn.lookupByID(domain_id)
                vms.append({
                    'id': domain.UUIDString(),
                    'name': domain.name(),
                    'state': 'running'
                })
                
            for domain_name in self.conn.listDefinedDomains():
                domain = self.conn.lookupByName(domain_name)
                vms.append({
                    'id': domain.UUIDString(),
                    'name': domain.name(),
                    'state': 'stopped'
                })
                
            return vms
            
        except libvirt.libvirtError as e:
            logger.error(f"Failed to list VMs: {e}")
            return []
