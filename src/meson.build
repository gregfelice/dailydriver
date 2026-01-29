# Use MODULE_DIR from parent meson.build (purelib path for mesonpy)
moduledir = MODULE_DIR

dailydriver_sources = [
  'dailydriver/__init__.py',
  'dailydriver/application.py',
  'dailydriver/window.py',
]

install_data(dailydriver_sources, install_dir: moduledir)

subdir('dailydriver/models')
subdir('dailydriver/services')
subdir('dailydriver/views')
subdir('dailydriver/resources')
