"""Direct native and media connections, independent of inherited proxies."""
import requests


def make_session():
    session = requests.Session()
    session.trust_env = False
    return session
