# Push current branch to origin and github remotes.
# Настройте оба remote один раз, см. README "Пуш в два remote".
$ErrorActionPreference = "Stop"
$branch = git rev-parse --abbrev-ref HEAD
git push origin $branch
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
git push github $branch
