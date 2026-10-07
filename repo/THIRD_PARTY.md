# 第三方依赖

没有打包第三方源代码、轮子或node_modules。Python固定依赖与许可METADATA记录在SBOM.json，require-hashes锁在requirements.lock；官方版本页：

- [attrs 26.1.0](https://pypi.org/project/attrs/26.1.0/) — MIT
- [jsonschema 4.25.1](https://pypi.org/project/jsonschema/4.25.1/) — MIT
- [jsonschema-specifications 2025.9.1](https://pypi.org/project/jsonschema-specifications/2025.9.1/) — MIT
- [PyYAML 6.0.2](https://pypi.org/project/PyYAML/6.0.2/) — MIT
- [referencing 0.37.0](https://pypi.org/project/referencing/0.37.0/) — MIT
- [rpds-py 2026.6.3](https://pypi.org/project/rpds-py/2026.6.3/) — MIT
- [typing_extensions 4.16.0](https://pypi.org/project/typing_extensions/4.16.0/) — PSF-2.0

Node宿主依赖锁只作安装声明，未打包运行包；固定Pi依赖的197项声明已与隔离安装元数据定点核对，无缺失声明；npm ci --ignore-scripts及SDK导入通过。运行包不随本包分发，真实模型生命周期另行验收。

Pi锁包含197个依赖条目；许可来源为锁及隔离安装package.json。未声明许可的条目0个，详见SBOM，未分发其代码；宿主生命周期仍partial。
