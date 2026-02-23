
## 📚 Documentation
- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api/api.md)
- [Setup Guide](docs/setup.md)
- [Development Roadmap](docs/roadmap.md)

## 🧪 Testing
```bash
# Run unit tests
make test

# Run integration tests
make test-integration

# Run with coverage
make test-coverage
```

## 🤝 Contributing
Contributions are welcome! Please read our Contributing Guidelines and feel free to submit pull requests.

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🌟 Star History
If you find this project useful, please consider giving it a star! It helps others discover it.
# Example: Create a VM via API
```bash
curl -X POST http://localhost:8000/api/v1/vms \
	-H "Content-Type: application/json" \
	-d '{
		"name": "my-vm",
		"vcpus": 2,
		"memory": 4096,
		"image": "ubuntu-22.04.qcow2"
	}'
```
## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- libvirt and KVM (for production use)
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/cubasnik/CEE.git
cd CEE

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# Run the server
make run
```
# CEE (Cloud Execution Environment) 🚀

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/cubasnik/CEE)](https://github.com/cubasnik/CEE/issues)
[![GitHub stars](https://img.shields.io/github/stars/cubasnik/CEE)](https://github.com/cubasnik/CEE/stargazers)

**CEE** is a lightweight, open-source hypervisor for virtual machine management. It provides a clean REST API and orchestration layer for managing the complete lifecycle of virtual machines.

## ✨ Features

- **Complete VM Lifecycle Management** - Create, start, stop, restart, and delete VMs
- **RESTful API** - Full control via HTTP endpoints
- **Pluggable Drivers** - Support for multiple virtualization backends (KVM/libvirt, OpenStack)
- **Resource Scheduling** - Smart placement of VMs based on available resources
- **Network Management** - Create and manage virtual networks
- **Image Management** - Upload, store, and clone VM images
- **Multi-tenancy** - Isolate resources between different projects/users

## 🏗 Architecture

CEE/
├── lcm/ # Lifecycle Management (core orchestrator)
│   ├── api/           # REST API endpoints
│   ├── orchestrator/  # VM lifecycle orchestration
│   ├── scheduler/     # Resource scheduling
│   ├── drivers/       # Virtualization backends
│   └── db/            # Database models and repository
├── tests/             # Unit tests
├── integration/       # Integration tests
├── docs/              # Documentation
└── scripts/           # Utility scripts
