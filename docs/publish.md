# Publishing `we-together` to PyPI

## 前置

- 注册 [PyPI](https://pypi.org) 账号 + 2FA
- 注册 [TestPyPI](https://test.pypi.org) 账号（用于预发）
- 在 `~/.pypirc` 配置 API token（或导出 `TWINE_USERNAME=__token__` + `TWINE_PASSWORD=<pypi-token>`）
- GitHub 仓库添加 secret `PYPI_TOKEN` 后，仍必须通过手动 workflow dispatch 发布；不要 tag-push 自动发布。

## 流程

### 1. 更新版本

```bash
# 编辑 pyproject.toml 的 [project].version
# 同步 src/we_together/cli.py 的 VERSION
```

### 2. 构建

```bash
rm -rf dist/ build/ *.egg-info
python -m build --wheel --sdist
```

### 3. 本地验证

```bash
pip install --force-reinstall dist/we_together-X.Y.Z-py3-none-any.whl
we-together version
python scripts/release_strict_e2e.py --profile strict
cd webui && npm test -- --run && npm run build && npm run visual:check
```

### 4. 发布 TestPyPI

```bash
python -m twine check dist/we_together-X.Y.Z-py3-none-any.whl dist/we_together-X.Y.Z.tar.gz
python -m twine upload --repository testpypi dist/we_together-X.Y.Z-py3-none-any.whl dist/we_together-X.Y.Z.tar.gz
# 从 TestPyPI 安装验证：
pip install -i https://test.pypi.org/simple/ we-together==X.Y.Z
```

### 5. 发布 PyPI（正式）

```bash
python -m twine upload dist/we_together-X.Y.Z-py3-none-any.whl dist/we_together-X.Y.Z.tar.gz
```

### 6. Tag + 推送

```bash
git tag vX.Y.Z
git push --tags
```

GitHub Actions `publish.yml` 使用手动 `workflow_dispatch`，并在上传前运行 pytest、strict gate、build 和 twine check。

## Checklist

- [ ] pyproject.version 与 cli.VERSION 一致
- [ ] CHANGELOG 有该版本条目
- [ ] 所有 ADR 已 Accepted
- [ ] pytest 全绿
- [ ] strict product gate 全绿
- [ ] eval-relation 不回归
- [ ] README 顶部链接到最新 CHANGELOG
- [ ] docs/quickstart.md 命令全部可跑通
- [ ] schema 版本与 docs 同步

## Release Notes 模板

见 `docs/release_notes_template.md`
