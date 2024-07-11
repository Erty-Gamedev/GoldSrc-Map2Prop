# Contributing to Map2Prop

Contributions are always welcome!

## Issues

The easiest way to contribute is to head over to the [Issues](https://github.com/Erty-Gamedev/GoldSrc-Map2Prop/issues) page and suggest a new feature or report on a bug if there isn't an issue for it already. Be as detailed and specific as possible.

For bug reports, please include the application version and steps to reproduce the bug.<br />
Log files (from /logs) and input map file(s) used will be very helpful. 

## Pull Requests

The project has two primary branches: `main` and `dev`.<br />
New development is typically done on the `dev` branch, and once deemed ready, merged into `main` to create a new version.

Versions are numbered using [Semantic Versioning](https://semver.org/).<br />
That is, major version increment reflects incompatible API changes, minor version increment reflects added functionality while remaining backwards compatible, while patch version increment reflects backwards compatible bug fixes.

### Features / Fixes

1. Create a fork of the project and create a new branch from `dev`. Prefix the branch name with either `feature/` or `fix/` accordingly. If the branch is meant to solve a particular issue, include the issue number in the branch name.

2. Set up an environment for the project, such as by using PIP and VENV (https://docs.python.org/3/tutorial/venv.html) and installing the dependencies from requirements.txt to be able to run and test the code.

3. After adding the new code ensure existing unit tests are still passing locally (feel free to add your own unit tests if relevant to your changes) and that the application otherwise is behaving as it should.

   Take a moment to review your changes before committing them and opening a pull request.

4. Open a Pull Request and document the changes and their purpose. Please include a link to any relevant issues the branch is meant to fix.

5. Please resolve any suggested changes or comments by maintainers.

6. If approved, it will be merged with the project and released with the next version.

### Hotfixes

More serious issues that cannot wait for the next version must be done as a hotfix.

The process is similar to that of [Features / Fixes](#features--fixes) except a new branch should be made from `main` and prefixed with `hotfix/`.
