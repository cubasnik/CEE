from main import create_app
from lcm.drivers.openstack_driver import OpenStackDriver
from lcm.drivers.kvm.kvm_driver import KVMDriver
import os

# Создаем реальный драйвер (выберите один)
# driver = OpenStackDriver()  # для OpenStack
driver = KVMDriver()  # для KVM

# Создаем приложение с реальным драйвером
app = create_app(driver, "kvm")

if __name__ == '__main__':
    # Создаем директорию для изображений, если её нет
    os.makedirs('static/images', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    print("🚀 Сервер запущен на http://localhost:8000")
    print("📚 Документация: http://localhost:8000/api/docs")
    app.run(host='0.0.0.0', port=8000, debug=True)
