def test_import():
    import israel_bus_cli as ibc
    assert hasattr(ibc, '__version__')
    # search_address with empty query returns [] (no network)
    assert ibc.search_address("") == []
