"""Tests for KVM driver."""
import pytest
from unittest.mock import Mock, patch
from lcm.drivers.kvm.kvm_driver import KVMDriver

class TestKVMDriver:
    """Test suite for KVMDriver."""
    
    @patch('libvirt.open')
    def test_connect_success(self, mock_open):
        """Test successful connection to libvirt."""
        mock_open.return_value = Mock()
        driver = KVMDriver()
        
        result = driver.connect()
        
        assert result is True
        mock_open.assert_called_once_with("qemu:///system")
        
    @patch('libvirt.open')
    def test_connect_failure(self, mock_open):
        """Test connection failure."""
        mock_open.return_value = None
        driver = KVMDriver()
        
        result = driver.connect()
        
        assert result is False
        
    @patch('libvirt.open')
    def test_create_vm(self, mock_open):
        """Test VM creation."""
        mock_conn = Mock()
        mock_domain = Mock()
        mock_domain.UUIDString.return_value = "123e4567-e89b-12d3-a456-426614174000"
        mock_conn.defineXML.return_value = mock_domain
        mock_open.return_value = mock_conn
        
        driver = KVMDriver()
        result = driver.create_vm(
            name="test-vm",
            vcpus=2,
            memory_mb=2048,
            image_path="/var/lib/libvirt/images/test.qcow2"
        )
        
        assert result == "123e4567-e89b-12d3-a456-426614174000"
        mock_conn.defineXML.assert_called_once()
        mock_domain.create.assert_called_once()
        
    @patch('libvirt.open')
    def test_list_vms(self, mock_open):
        """Test listing VMs."""
        mock_conn = Mock()
        mock_conn.listDomainsID.return_value = [1]
        mock_conn.listDefinedDomains.return_value = ["stopped-vm"]
        
        mock_running_domain = Mock()
        mock_running_domain.UUIDString.return_value = "running-uuid"
        mock_running_domain.name.return_value = "running-vm"
        mock_conn.lookupByID.return_value = mock_running_domain
        
        mock_stopped_domain = Mock()
        mock_stopped_domain.UUIDString.return_value = "stopped-uuid"
        mock_stopped_domain.name.return_value = "stopped-vm"
        mock_conn.lookupByName.return_value = mock_stopped_domain
        
        mock_open.return_value = mock_conn
        
        driver = KVMDriver()
        driver.connect()
        vms = driver.list_vms()
        
        assert len(vms) == 2
        assert vms[0]['name'] == "running-vm"
        assert vms[0]['state'] == "running"
        assert vms[1]['name'] == "stopped-vm"
        assert vms[1]['state'] == "stopped"
