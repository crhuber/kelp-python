import requests
import click
import json
import pprint
import sys
import os
from pathlib import Path


# CONFIG
home = str(Path.home())
DEW_DIR = home + '/.dew/'
DOWNLOAD_DIR =  home +'/.dew/packages/' #needs the trailing slash


def load_config():
    try:
        with open(DEW_DIR + '.dew.json') as file:
            packages = json.load(file)
            return packages
    except FileNotFoundError:
        print("Kelp config file not found")
        sys.exit(1)


def get_release(packages):
    for package in packages:
        owner, repo = package.split("/")
        release = packages[package]
        r = requests.get('https://api.github.com/repos/{}/{}/releases/{}'.format(owner, repo, release))
        response = r.json()
        try:
            assets = response['assets']
            for asset in assets:
                mac_identifiers = ['mac', 'macOs', 'darwin']
                ## TODO add .dmg support
                if any(word in asset['browser_download_url'] for word in mac_identifiers) and asset['browser_download_url'].endswith(('zip', '.gz')):
                    print("downloading {}:{}".format(package, release))
                    rd = requests.get(asset['browser_download_url'])
                    with open(DOWNLOAD_DIR + asset['name'], 'wb') as f:
                        f.write(rd.content)
        except KeyError:
            print("no assets found for {}".format(package))

@click.command()
def init():
    os.mkdir(DEW_DIR)
    os.mkdir(DOWNLOAD_DIR)

@click.command()
def list():
    packages = load_config()
    pprint.pprint(packages)

@click.command()
def install():
    with open(DEW_DIR + '.dew.json') as file:
        packages = json.load(file)
        get_release(packages)

@click.group()
def cli():
    pass

cli.add_command(list)
cli.add_command(install)
cli.add_command(init)

if __name__ == "__main__":
    cli()