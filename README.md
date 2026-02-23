# ☁️ CEE — Cloud Execution Environment

CEE is a lightweight hypervisor and orchestration framework for managing virtual machines across multiple backends (KVM, OpenStack, and more).

---

## ✨ Features

- 🔧 Lifecycle Management (LCM) for VMs
- 🌐 REST API for VM operations
- 🧩 Pluggable drivers (KVM, OpenStack)
- 📦 Python 3.12+ support
- ✅ Tested with `pytest` and high coverage
- 🐳 Ready for containerization (Docker)

---

## 🚀 Quick Start

### Prerequisites

- Python **3.12** (recommended, tested)
- `libvirt` and `libvirt-dev` (for KVM driver)
- Virtual environment (recommended)
- Git

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/cubasnik/CEE.git
cd CEE

# 2. Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Install additional required packages
pip install fastapi uvicorn python-multipart
pip install openstacksdk python-openstackclient
pip install libvirt-python

# 5. Install system dependencies (Linux/WSL only)
sudo apt update
sudo apt install libvirt-dev pkg-config

# 6. Verify installation
pytest tests/ -v
## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

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
├── lcm/                    # Lifecycle Manager core
│   ├── api/                # API endpoints
│   ├── drivers/            # Backend drivers
│   │   ├── kvm/            # KVM driver
│   │   └── openstack_driver.py  # OpenStack driver
│   └── models/             # Data models
├── cee-lcm/                # CEE-specific extensions
├── tests/                   # Unit and integration tests
│   ├── unit/               # Unit tests
│   │   ├── api/            # API tests
│   │   └── drivers/        # Driver tests
│   └── integration/         # Integration tests
├── docs/                    # Documentation
│   ├── architecture.md      # Architecture overview
│   ├── api/                 # API documentation
│   └── setup.md             # Setup guide
├── scripts/                 # Helper scripts
├── static/                  # Static files
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── pyproject.toml           # Project config (pytest, etc.)
├── main.py                  # Application entry point
└── README.md                # This file
