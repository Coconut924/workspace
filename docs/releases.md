# Packaging and Homebrew releases

The source lives at https://github.com/Coconut924/workspace. The shared tap lives
at https://github.com/Coconut924/homebrew-tap and may contain other formulas.
Users install the standalone executable with:

```sh
brew tap Coconut924/tap
brew install Coconut924/tap/workspace
```

The installed tool needs neither Python nor this checkout. It still needs iTerm2
and API authorization. YAML presets remain in the user's configuration directory.

## Local development and packaging

```sh
mise install
mise run setup
mise run test
mise run lint
mise run build
dist/workspace --help
mise run package
```

PyInstaller is a pinned development dependency in the project's virtual
environment. `mise.toml` pins Python and `constraints-build.txt` pins the verified
build/runtime dependencies. Refresh these deliberately when upgrading, run the
tests, and rebuild both architectures. Builds are repeatable with these versions;
archive hashes can differ because archives contain build timestamps.
`build` embeds Python and runtime dependencies in `dist/workspace`,
then runs it outside the checkout with a system-only PATH. `package` builds the
executable and creates `dist/workspace-VERSION-macos-ARCH.tar.gz` containing the
binary, README and example configurations, plus a `.sha256` file. These generated
files are ignored by Git. Development still uses the editable installation in
`.venv`; rebuilding is needed to update the standalone executable.

Build each architecture with a native Python environment on that architecture.
The release workflow uses `macos-15` for Apple Silicon and `macos-15-intel` for
Intel. Builds are tested on macOS 15; older macOS releases are not currently
verified. Do not combine PyInstaller one-file executables with `lipo`.

PyInstaller signs embedded binaries ad hoc for macOS. These releases are not
Developer ID signed or notarized. Downloaded executables can require normal
macOS approval; do not disable Gatekeeper. A Developer ID distribution pipeline
can be added later when signing credentials are available.

## Publish a new version

Requires an authenticated GitHub CLI (`gh auth login`), push access to both repos,
and GitHub Actions enabled in `Coconut924/workspace`. No cross-repository token is
needed in Actions: it uploads the source repo's release, and you push the tap with
your local GitHub credentials.

1. Update the version in **both** `pyproject.toml` and
   `src/workspace/__init__.py` (for example `0.2.0`). Keep them identical.
2. Run `mise run test`, `mise run lint`, and `mise run package`. On a Mac with
   iTerm API access, run the standalone binary against `examples/demo.yaml`
   and verify the workspace. A new build may prompt for authorization.
3. Commit the changes and push the version tag:

   ```sh
   git add pyproject.toml src/workspace/__init__.py
   # Also stage the source changes you intend to release
   git commit -m 'Release 0.2.0'
   git push origin main
   git tag v0.2.0
   git push origin v0.2.0
   ```

4. Wait for the release workflow to finish:

   ```sh
   gh run list --repo Coconut924/workspace --workflow release.yml
   gh run watch RUN_ID --repo Coconut924/workspace --exit-status
   gh release view v0.2.0 --repo Coconut924/workspace
   ```

   Both native archives and `SHA256SUMS` must be present. A manual Actions run
   builds downloadable artifacts without publishing a release. Tag/version
   mismatches fail before packaging. If a build fails, fix it and release a new
   version; don't silently replace assets already used by a published formula.

5. Preview and publish the tap update from this source checkout:

   ```sh
   .venv/bin/python scripts/publish_tap.py --version 0.2.0 --dry-run
   mise run publish-tap
   ```

   The default version comes from `pyproject.toml`. The script downloads both
   release archives and `SHA256SUMS`, verifies their contents' hashes, generates
   `Formula/workspace.rb`, clones the tap temporarily, and commits and pushes
   only that formula. Other formulas remain untouched. It does not overwrite
   release assets. Identical formula content is a no-op. Use `--version` to target
   a particular published stable version. A tap push fails safely if someone
   else changed the branch; rerun to start from the latest checkout.

6. Verify the published installation:

   ```sh
   brew update
   brew upgrade Coconut924/tap/workspace
   brew test Coconut924/tap/workspace
   workspace --version
   ```

   On the first installation use `brew install` instead of `brew upgrade`.
   Homebrew picks the matching architecture and verifies the formula checksum.
   The formula installs examples under `brew --prefix workspace` in
   `share/workspace/examples`. To add another tool, add another Ruby file to the
   shared tap's `Formula/` directory.

References: [PyInstaller macOS architectures and signing](https://pyinstaller.org/en/stable/feature-notes.html),
[Homebrew taps](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap), and
[GitHub runner architectures](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
