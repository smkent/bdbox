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

Run `mise install` in new repository clones to:

* Enable git hooks
* Install UI dependencies via `npm`
  (To update, run `mise install` again or `npm install`)
* Install [Playwright][playwright] UI testing browser packages
  (To update, run `mise install` again or `playwright install`)
* Build static UI assets
  (To build again, run `mise run static` or `mise run dev`)

```sh
mise install
```

## Development tools

* `mise run dev`: Watch and automatically rebuild static UI assets on changes
* `mise run lint`: Run formatters and static checks
* `mise run static`: Build static UI assets
* `mise run test`: Run backend tests
* `mise run webtest`: Run frontend tests

The `lint` and `test` tasks can also be run as a single combined command with:

```sh
mise run lt
```

### Test snapshots

Some tests compare test results with saved snapshots. Test snapshots can be
updated by running:

```sh
mise run snapup
```

## Documentation server

Start the development server with:

```sh
mise run docs
```

The documentation site will be served at:

[**http://localhost:8000**](http://localhost:8000){ .md-button .md-button--primary target="_blank" }

To use a different bind host/port, run `mise run docs --help` for usage info.

[playwright]: https://playwright.dev
