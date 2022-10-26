# Maconomy life-hack

Report your weekly time with bash, the code is so and so but it works... no tests, its just a POC

## Install

There is no package to install, you need to create it locally and install it to /usr/local/bin folder.

```bash
make install
make create-bundle
make install-bundle 
```

## How to use

### Report

You report time like this:

```bash
maconomy report -u "username" -p "password" -r 8 -t "8,8,8,8,8"
```

Limitation: You can only report time for a row number and for all 5 days in work week

### Submit

Is not yet implemented but will work like this

```bash
maconomy submit -u "username" -p "password"
```

## Future

* Will make it possible to report individual days

## Contribute

Please contribute to this if you like.
