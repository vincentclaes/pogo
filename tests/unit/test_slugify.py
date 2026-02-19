from biosignal.notebook_builder import _slugify


def test_slugify_basic():
    value = "Top Upregulated Genes After Dexamethasone (Dex) Treatment!!"
    assert _slugify(value) == "top-upregulated-genes-after-dexamethasone-dex"


def test_slugify_short():
    assert _slugify("Hello World") == "hello-world"


def test_slugify_empty():
    assert _slugify("   ") == ""
