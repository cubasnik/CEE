"""Mock driver for testing without actual virtualization."""
import uuid
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MockDriver:
    """Mock driver that simulates VM operations without actual virtualization."""
    
    def __init__(self, connection_uri: str = None):
        """Initialize mock driver."""
        self.vms = {}
        self.connected = True
        self.connection_uri = connection_uri
        logger.info("Mock driver initialized")
        
    def connect(self) -> bool:
        """Simulate connection."""
        logger.info("Mock driver connected")
        return True
        
    def disconnect(self):
        """Simulate disconnection."""
        logger.info("Mock driver disconnected")
        
    def create_vm(self, name: str, vcpus: int, memory_mb: int, image_path: str) -> Optional[str]:
        """Simulate VM creation."""
        vm_id = str(uuid.uuid4())
        self.vms[vm_id] = {
            'id': vm_id,
            'name': name,
            'vcpus': vcpus,
            'memory_mb': memory_mb,
            'image_path': image_path,
            'state': 'running',
            'created': True
        }
        logger.info(f"Mock VM {name} created with ID: {vm_id}")
        return vm_id
        
    def list_vms(self) -> List[Dict[str, Any]]:
        """List all mock VMs."""
        return list(self.vms.values())
        
    def get_vm(self, vm_id: str) -> Optional[Dict[str, Any]]:
        """Get VM details by ID."""
        return self.vms.get(vm_id)
        
    def delete_vm(self, vm_id: str) -> bool:
        """Simulate deleting VM."""
        if vm_id in self.vms:
            del self.vms[vm_id]
            logger.info(f"Mock VM {vm_id} deleted")
            return True
        return False
