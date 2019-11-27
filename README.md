<p align="center">
  <img height="150px" src="./logo.png"  alt="KELP" title="KELP">
</p>
# KELP
A simple python replacement for homebrew for installing binary packages on MacOS

## Why?

I built Kelp to scratch my own itch while using Homebrew. For example if you use homebrew to install terraform, it is
cumberson to switch between different terraform versions. Here is why I built Kelp:

* No waiting for a formula to become available on homebrew
* Switch between different versions of a package easily
* Keep all your computers up to date with a single installation manifest
* Install multiple packages at one time.


## How Does it Work?

It downloads all the packages in a `~/.kelp/.kelp.json` file to `~/.kelp/bin`. It can download any binary file on github releases.

## How Do I Use It?

1. Download the latest `kelp` release from github releases
2. Initliaze Kelp

    `kelp init`

3. Add kelp to your PATH

    `export PATH=~/.kelp/bin/:$PATH`

4. Add a new package

    `kelp add wercker/stern:latest`

4. Install

    `kelp install`


### How do I install multiple packages at one time?

1. Edit  `~/.kelp/.kelp.json` and add all your favorite packages there. For example mine looks ike

```
{
    "sharkdp/fd": "latest",
    "sharkdp/bat": "latest",
    "ubnt-intrepid/dot": "latest",
    "tsenart/vegeta": "latest",
    "junegunn/fzf-bin": "latest",
    "termit/flycut": "latest",
    "rxhanson/rectangle": "latest",
    "lwouis/alt-tab-macos": "latest",
    "versent/saml2aws": "latest",
    "watchexec/watchexec": "latest",
    "wercker/stern": "latest",
    "hashicorp/terraform": "https://releases.hashicorp.com/terraform/0.11.14/terraform_0.11.14_darwin_amd64.zip",
    "ogham/exa": "latest",
    "Marginal/QLVideo": "latest",
    "JohnCoates/Aerial": "latest",
    "istio/istio": "latest",
    "aws/aws-iam-authenticator": "https://amazon-eks.s3-us-west-2.amazonaws.com/1.14.6/2019-08-22/bin/darwin/amd64/aws-iam-authenticator",
    "helm/helm": "v2.16.0"
}
```

2. Run kelp

    `kelp install`

### What if the package I want is not on github releases?

Easy. Just add the http(s) link to the binary like so to your .kelp.json file

`
kelp add hashicorp/terraform https://releases.hashicorp.com/terraform/0.11.13/terraform_0.11.13_darwin_amd64.zip
`


## Troubleshooting

### Why wasnt my package installed ?

Kelp looks for binaries made for MacOS, if it finds a binary for linux or windows it will skip downloading it. 

### Why is kelp so slow?

I used PyInstaller to freeze this Python applications into stand-alone executable which means its a little slow when executing

### Does it work for Linux?

Not yet

