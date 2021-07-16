with open(os.path.join(plugin_dir, 'version.json')) as f:
    version_info = json.load(f)

__version__ = version_info['version']
__version_major__ = re.sub(r'([0-9]+)(\.[0-9]+)+$', r'\g<1>', __version__)
__revision__ = version_info['revision']
__release_date__ = version_info['release_date']
