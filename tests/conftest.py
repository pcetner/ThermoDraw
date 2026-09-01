def pytest_addoption(parser):
    parser.addoption(
        "--update-goldens", action="store_true", default=False,
        help="rewrite the golden SVGs from current output, then skip")
