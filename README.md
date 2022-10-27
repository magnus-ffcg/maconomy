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

### Report time for your weekly timereport

You report time like this, basically saying which row and hours per day (5 days)
If you are unsure which row to use, please use the "view" command.

```bash
maconomy report -a "https://xxxx-iaccess.deltekfirst.com/maconomy-api/containers/xxxx/" -u "username" -p "password" -r 8 -t "8,8,8,8,8"
```

Limitation: You can only report for the entire week at once

### View your weekly timereport

List the current timereport

```bash
maconomy view -a "https://xxxx-iaccess.deltekfirst.com/maconomy-api/containers/xxxx/" -u "username" -p "password"
```

### Submit

Please keep in mind that submitting should be the last thing you do, as it will lock your timesheet.

```bash
maconomy submit -a "https://xxxx-iaccess.deltekfirst.com/maconomy-api/containers/xxxx/" -u "username" -p "password"
```

## Future

* Will make it possible to report individual days

## Contribute

Please contribute to this if you like.
