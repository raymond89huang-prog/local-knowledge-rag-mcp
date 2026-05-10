from doc_rag.config import AppConfig


def test_config_loads_multiple_vaults_and_expands_paths(tmp_path):
    vault_dir = tmp_path / "Product Docs"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
embedding:
  model_name: "test-model"
vaults:
  product-docs:
    description: "Product knowledge"
    path: "{vault_dir.as_posix()}"
    include:
      - "**/*.md"
  research:
    path: "~/Knowledge/Research"
search:
  default_top_k: 3
""",
        encoding="utf-8",
    )

    config = AppConfig.from_yaml(str(config_path))

    assert [vault.name for vault in config.list_vaults()] == ["product-docs", "research"]
    assert config.get_vault("product-docs").description == "Product knowledge"
    assert config.search.default_top_k == 3
    assert config.get_vault("product-docs").resolved_path().name == "Product Docs"

