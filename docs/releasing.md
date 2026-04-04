---
title: Releasing a new version
icon: lucide/rocket
---

# Releasing a new version

Release version numbers should follow [Semantic Versioning][semver].

To create a new release, simply create and push a tag with the new release
version number:

```sh
git tag vX.Y.Z  # for example, v1.2.3
git push --tags
```

* A corresponding [GitHub release][github-releases]
  will be created automatically.

    [![GitHub Release][github-release-badge]][github-release-latest]

* A release package will be built and [uploaded to PyPI][pypi-project].

    [![PyPI][pypi-badge]][pypi-project]

[github-release-badge]: https://img.shields.io/github/v/release/smkent/bdbox
[github-release-latest]: https://github.com/smkent/bdbox/releases/latest
[github-releases]: https://github.com/smkent/bdbox/releases
[pypi-badge]: https://img.shields.io/pypi/v/bdbox
[pypi-project]: https://pypi.org/project/bdbox/
[semver]: https://semver.org/
