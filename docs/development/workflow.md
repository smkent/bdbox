---
title: Development workflow
icon: lucide/braces
---

# Project development workflow

## Cloning the repository

```sh
git clone https://github.com/smkent/bdbox
cd bdbox
```

Run `poe setup` in new repository clones to:

* Enable git hooks
* Install UI dependencies via `npm`
  (To update, run `poe setup` again or `npm install`)
* Install [Playwright][playwright] UI testing browser packages
  (To update, run `poe setup` again or `playwright install`)
* Build static UI assets
  (To build again, run `poe static` or `poe dev`)

```sh
poe setup
```

## Development tools

* `poe dev`: Watch and automatically rebuild static UI assets on changes
* `poe lint`: Run formatters and static checks
* `poe static`: Build static UI assets
* `poe test`: Run backend tests
* `poe webtest`: Run frontend tests

The `lint` and `test` tasks can also be run as a single combined command with:

```sh
poe lt
```

### Test snapshots

Some tests compare test results with saved snapshots. Test snapshots can be
updated by running:

```sh
poe snapup
```

## Documentation server

Start the development server with:

```sh
poe docs
```

The documentation site will be served at:

[**http://localhost:8000**](http://localhost:8000){ .md-button .md-button--primary target="_blank" }

To use a different bind host/port, run `poe --help docs` for arguments info.

[playwright]: https://playwright.dev
