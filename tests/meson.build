# Tests meson.build
# Python tests are run via pytest; C tests compiled with meson

# Python test discovery (for convenience with `meson test`)
python3 = find_program('python3')

test('test_config_generation',
  python3,
  args: ['-m', 'pytest', '-xvs', files('test_config_generation.py')],
  workdir: meson.current_source_dir(),
  timeout: 30,
)

test('test_cert_parsing',
  python3,
  args: ['-m', 'pytest', '-xvs', files('test_cert_parsing.py')],
  workdir: meson.current_source_dir(),
  timeout: 30,
)

test('test_security',
  python3,
  args: ['-m', 'pytest', '-xvs', files('test_security.py')],
  workdir: meson.current_source_dir(),
  timeout: 30,
)

test('test_integration',
  python3,
  args: ['-m', 'pytest', '-xvs', files('test_integration.py')],
  workdir: meson.current_source_dir(),
  timeout: 60,
)
