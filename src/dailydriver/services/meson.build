services_sources = [
  '__init__.py',
  'gsettings_service.py',
  'hardware_service.py',
  'hid_apple_service.py',
  'keyboard_config_service.py',
  'profile_service.py',
  'tiling_service.py',
]

install_data(services_sources, install_dir: moduledir / 'services')

# Backends subpackage
backends_sources = [
  'backends/__init__.py',
  'backends/base.py',
  'backends/detection.py',
  'backends/factory.py',
  'backends/gnome.py',
  'backends/kde.py',
]

install_data(backends_sources, install_dir: moduledir / 'services' / 'backends')
