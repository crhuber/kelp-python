import requests
import click
import json
import pprint
import sys

# CONFIG 
KELP_DIR = '~/.kelp/' 
DOWNLOAD_DIR = '~/.kelp/packages/' #needs the trailing slash


def load_config():
    try:
        with open(KELP_DIR + '.kelp.json') as file:
            packages = json.load(file)
            return packages
    except FileNotFoundError:
        print("Kelp config file not found")
        sys.exit(1)


def get_release(packages):
    for dl in packages:
        username, repo = dl.split("/")
        r = requests.get('https://api.github.com/repos/{}/{}/releases/latest'.format(username, repo))
        response = r.json()
        assets = response['assets']
        for asset in assets:
            mac_identifiers = ['mac', 'macOs', 'darwin']
            ## TODO add .dmg support
            if any(word in asset['browser_download_url'] for word in mac_identifiers) and asset['browser_download_url'].endswith(('zip', '.gz')):
                print("downloading {}".format(dl))
                rd = requests.get(asset['browser_download_url'])
                with open(DOWNLOAD_DIR + asset['name'], 'wb') as f:
                    f.write(rd.content)

@click.command()
def init():
    os.mkdir(KELP_DIR)
    os.mkdir(DOWNLOAD_DIR)

@click.command()
def list():
    packages = load_config()
    pprint.pprint(packages)

@click.command()
def install():
    with open(KELP_DIR + '.kelp.json') as file:
        packages = json.load(file)
        get_release(packages)

@click.group()
def cli():
    pass

cli.add_command(list)
cli.add_command(install)


if __name__ == "__main__":
    cli()