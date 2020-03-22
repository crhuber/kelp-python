import json
import os
import pprint
import re
import shutil
import sys
import tarfile
import tempfile
import time
import stat
import webbrowser
import subprocess
from os import path, walk
from os.path import isfile, join
from pathlib import Path
from subprocess import run
from zipfile import ZipFile

import click
import filetype
import requests

# CONFIG
home = str(Path.home())
KELP_DIR = home + '/.kelp/'
KELP_BIN = home + '/.kelp/bin/'
CACHE_DIR = home + '/.kelp/cache/'  # needs the trailing slash


def load_config():
    try:
        with open(KELP_DIR + '.kelp.json', 'r') as file:
            packages = json.load(file)
            file.close()
            return packages
    except FileNotFoundError:
        print("Kelp config file not found")
        sys.exit(1)


def file_is_binary(filepath):
    signatures = [
        "CF FA ED FE",
        "50 4B 03 04",
        "1F 8B 08 00",
        "CF FA ED FE",
    ]
    try:
        file = open(filepath, "rb").read(32)
        hex_bytes = " ".join(['{:02X}'.format(byte) for byte in file])
        # print(f"{filepath}: {hex_bytes}")
        for signature in signatures:
            if hex_bytes.startswith(signature) and not filepath.endswith((".dylib", ".tgz", ".gz", ".zip", ".pkg", ".app", ".saver")):
                return True
        return False
    except IsADirectoryError:
        return False


def unzip_file(filepath):
    print(f"Unzipping {filepath}")
    extract_dir = tempfile.mkdtemp()
    with ZipFile(filepath, 'r') as zipObj:
        zipObj.extractall(path=extract_dir)
    return extract_dir


def untar_file(filepath):
    print(f"Unzipping {filepath}")
    extract_dir = tempfile.mkdtemp()
    with tarfile.open(filepath) as tar:
        tar.extractall(path=extract_dir)
    return extract_dir


def exists_in_cache(filepath):
    return path.exists(filepath)


def download(download_url, filename):
    print(f"Downloading {filename}")
    downloaded = False
    try:
        response = requests.get(download_url)
        with open(CACHE_DIR + filename, 'wb') as f:
            f.write(response.content)
        downloaded = True
        return downloaded
    except:
        return downloaded


def extract_package(filepath):
    extract_dir = None
    if filepath.endswith(".zip"):
        extract_dir = unzip_file(filepath)
    elif filepath.endswith(".xz"):
        extract_dir = untar_file(filepath)
    elif filepath.endswith(".tgz"):
        extract_dir = untar_file(filepath)
    elif filepath.endswith(".gz"):
        extract_dir = untar_file(filepath)
    elif filepath.endswith(".xz"):
        extract_dir = untar_file(filepath)
    # some files come downloaded unzipped
    elif file_is_binary(filepath):
        print(f"{filepath} already unzipped and a binary copying to kelp bin..")
        shutil.copy2(filepath, KELP_BIN)
    else:
        print(f"{filepath} is not an archive")
    return extract_dir


def move_binaries(extract_dir):
    for (dirpath, dirnames, filenames) in walk(extract_dir):
        # dont walk the contents of .app files.
        if ".app" in dirpath:
            pass
        else:
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if file_is_binary(filepath):
                    print(f"Moving executable {filename} to Kelp bin..")
                    shutil.copy2(filepath, KELP_BIN)


def make_binaries_executable():
    for (dirpath, dirnames, filenames) in walk(KELP_BIN):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if file_is_binary(filepath):
                # add executable bit to file
                st = os.stat(filepath)
                os.chmod(filepath, 0o775)


def find_release_assets(owner, repo, release):
    """Makes a request to github and finds all releases for a repo"""
    api_token = os.getenv('GITHUB_TOKEN', None)
    api_username = os.getenv('GITHUB_USERNAME', None)
    try:
        # else just get the latest
        if release == "latest":
            if api_token and api_username:
                r = requests.get(
                    f'https://api.github.com/repos/{owner}/{repo}/releases/{release}', auth=(api_username, api_token))
            else:
                r = requests.get(
                    f'https://api.github.com/repos/{owner}/{repo}/releases/{release}')
            response = r.json()
            assets = response['assets']
            return assets
        else:
            # get releases by tag
            if api_token and api_username:
                r = requests.get(
                    f'https://api.github.com/repos/{owner}/{repo}/releases', auth=(api_username, api_token))
            else:
                r = requests.get(
                    f'https://api.github.com/repos/{owner}/{repo}/releases')
            response = r.json()
            for rel in response:
                if rel['tag_name'] == release:
                    return rel['assets']
    except Exception as e:
        print(f"✗ Error connecting to github: \n {e}")


def download_package(package, release):
    owner, repo = package.split("/")
    install_result = {}
    # support http projects
    if release.startswith("http"):
        # split url path and grab last element
        filename = release.split("/")[-1]
        filepath = os.path.join(CACHE_DIR, filename)
        if exists_in_cache(filepath):
            print(
                f"Skipping download.. {filename} already exists in cache")
        else:
            download(release, filename)
        install_result['filepath'] = filepath
    else:
        # support github projects
        assets = find_release_assets(owner, repo, release)
        if assets:
            asset_dl_url = get_asset_dl_url(assets)
            if 'browser_download_url' in asset_dl_url:
                download_url = asset_dl_url['browser_download_url']
                filename = asset_dl_url['filename']
                filepath = os.path.join(CACHE_DIR, filename)
                if exists_in_cache(filepath):
                    print(
                        f"Skipping download.. {filename} already exists in cache.. ")
                else:
                    download(download_url, filename)
                install_result['filepath'] = filepath
    return install_result


def get_asset_dl_url(assets):
    """
    For a list of given release assetes, tries to find one for mac that is appropriate
    """
    download = {}
    for asset in assets:
        # download mac binaries
        mac_identifiers = ['mac', 'macOs', 'macos', 'darwin', 'osx']
        if any(word in asset['browser_download_url'] for word in mac_identifiers):
            if asset['browser_download_url'].endswith(('.zip', '.tar', '.gz', '.xz', '.dmg', '.pkg', '.tgz')):
                download['browser_download_url'] = asset['browser_download_url']
                download['filename'] = asset['name']
            # skip ones like sha256 for example istio-1.4.0-osx.tar.gz.sha256
            elif asset['browser_download_url'].endswith(('.sha256')):
                continue
            else:
                # some releases like stern dont have an extension: ie stern_darwin_amd64
                download['browser_download_url'] = asset['browser_download_url']
                download['filename'] = asset['name']
        # some packages are made specifically for mac. ie: screensavers, apps
        elif asset['browser_download_url'].endswith((".dmg", ".pkg", ".saver.zip", "app.zip")):
            download['browser_download_url'] = asset['browser_download_url']
            download['filename'] = asset['name']

    return download


def find_fullpkg_name(packages, shortname):
    """ Allow users to use shortname istio instead of istio/istio """
    package_found = False
    for pkg in packages:
        psplit = pkg.split("/")
        prepo = psplit[-1]
        if prepo == shortname:
            package_found = True
            return pkg
    if not package_found:
        print(f"Package not found in your config, try installing it first")
        exit()


@click.command()
def init():
    if not os.path.isdir(KELP_DIR):
        os.mkdir(KELP_DIR)
    if not os.path.isdir(KELP_BIN):
        os.mkdir(KELP_BIN)
    if not os.path.isdir(CACHE_DIR):
        os.mkdir(CACHE_DIR)
    print(
        f"🗒 Add Kelp to your path by running \nexport PATH={KELP_BIN}:$PATH")


@click.command()
def list():
    packages = load_config()
    for package, release in packages.items():
        print(f"{package}:{release}")


@click.command()
@click.argument('package')
def update(package):
    packages = load_config()
    try:
        try:
            release = packages[package]
        except KeyError:
            # allow users to use shortname istio instead of istio/istio
            package = find_fullpkg_name(packages, package)
            release = packages[package]
        download_result = download_package(package, release)
        if download_result:
            extract_dir = extract_package(download_result['filepath'])
            if extract_dir:
                move_binaries(extract_dir)
            make_binaries_executable()
            print(f"✓ Installed {package}:{release}")
        else:
            print(f"✗ Error installing {package}:{release}")
    except Exception as e:
        print(f"✗ Error installing {package}:{release}. \n {e}")


@click.command()
def install():
    packages = load_config()
    for package in packages:
        print(f"\n===> Installing {package}")
        try:
            try:
                release = packages[package]
            except KeyError:
                # allow users to use shortname istio instead of istio/istio
                package = find_fullpkg_name(packages, package)
                release = packages[package]
            download_result = download_package(package, release)
            if download_result:
                extract_dir = extract_package(download_result['filepath'])
                if extract_dir:
                    move_binaries(extract_dir)
                print(f"✓ Installed {package}:{release}")
            else:
                print(f"✗ Error installing {package}:{release}")
        except Exception as e:
            print(f"✗ Error installing {package}:{release}. \n{e}")
        time.sleep(0.7)
    make_binaries_executable()
    print(f"\n✅ Done!")


@click.command()
@click.argument('package')
@click.argument('release', required=False)
def add(package, release="latest"):
    match = re.search("\d+\.\d+.\d+", release)
    if not match:
        if not release.startswith("http"):
            if release != "latest":
                raise click.BadParameter(
                    'Invalid release name, it shouild either be latest, an http link or semvar format')

    if len(package.split("/")) != 2:
        raise click.BadParameter(
            'Invalid package name, it should follow username/repo format')

    packages = load_config()
    packages[package] = release

    with open(KELP_DIR + '.kelp.json', "w") as file:
        json.dump(packages, file, indent=4)


@click.command()
@click.argument('package')
def remove(package):
    packages = load_config()
    packages.pop(package)

    with open(KELP_DIR + '.kelp.json', "w") as file:
        json.dump(packages, file, indent=4)


@click.command()
def inspect():
    subprocess.call(['open', KELP_DIR])


@click.command()
@click.argument('package')
def browse(package):
    packages = load_config()
    package = find_fullpkg_name(packages, package)
    url = 'https://github.com/' + package
    webbrowser.open(url, new=2)


@click.command()
def upgrade():
    package = "crhuber/kelp"
    release = "latest"
    owner, repo = package.split("/")
    try:
        print(f"\n===> Upgrading {package}")
        assets = find_release_assets(owner, repo, release)
        for asset in assets:
            if 'browser_download_url' in asset:
                download_url = asset['browser_download_url']
                filename = 'kelp'
                download(download_url, filename)
                print(f"\n✅ Kelp downloaded to: {CACHE_DIR}{filename}")

    except Exception as e:
        print(f"✗ Error installing {package}:{release}. \n{e}")


def find_semver(version_str):
    rexpression = "v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
    match = re.search(rexpression, version_str)
    if match:
        return match[0]
    else:
        return None


def find_local_version(package):
    try:
        process = subprocess.run([package, 'version'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 universal_newlines=True)
        if process.returncode == 0:
            version = find_semver(process.stdout)
            print(f'===> {package} local version: {version}')
        elif process.returncode == 1 or 2:
            process = subprocess.run([package, '--version'],
                                     stdout=subprocess.PIPE,
                                     universal_newlines=True)
            version = find_semver(process.stdout)
            print(f'===> {package} local version: {version}')
        else:
            print(f'===> {package} could not find version')

    except FileNotFoundError:
        print(f"{package} not installed")


def find_remote_version(package):
    # allow users to use shortname istio instead of istio/istio
    packages = load_config()
    package = find_fullpkg_name(packages, package)
    owner, repo = package.split("/")

    api_token = os.getenv('GITHUB_TOKEN', None)
    api_username = os.getenv('GITHUB_USERNAME', None)
    release = "latest"
    if api_token and api_username:
        r = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/releases/{release}', auth=(api_username, api_token))
    else:
        r = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/releases/{release}')
    response = r.json()
    version = response['tag_name']
    print(f'===> {package} remote version: {version}')


@click.command()
@click.argument('package')
def version(package):
    find_remote_version(package)
    find_local_version(package)


@click.group()
def cli():
    pass


cli.add_command(list)
cli.add_command(install)
cli.add_command(init)
cli.add_command(add)
cli.add_command(update)
cli.add_command(remove)
cli.add_command(inspect)
cli.add_command(browse)
cli.add_command(upgrade)
cli.add_command(version)
