import importlib
import sys
import types
import unittest


def load_app_module():
    class DummySessionState(dict):
        pass

    class DummyStreamlit:
        def __init__(self):
            self.secrets = {}
            self.session_state = DummySessionState()
            self.sidebar = type(
                "Sidebar",
                (),
                {
                    "title": lambda *args, **kwargs: None,
                    "radio": lambda *args, **kwargs: None,
                    "text_input": lambda *args, **kwargs: "Operador",
                },
            )()

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

        def cache_resource(self, func):
            return func

        def stop(self):
            raise RuntimeError("stop called")

    fake_streamlit = DummyStreamlit()
    fake_streamlit.__package__ = "streamlit"
    sys.modules["streamlit"] = fake_streamlit

    fake_supabase = types.ModuleType("supabase")
    fake_supabase.create_client = lambda url, key: {"url": url, "key": key}
    fake_supabase.Client = object
    sys.modules["supabase"] = fake_supabase

    sys.modules.pop("app", None)
    return importlib.import_module("app")


class AppLogicTests(unittest.TestCase):
    def test_missing_supabase_config_uses_local_storage(self):
        app = load_app_module()

        self.assertIsNone(app.init_supabase())
        self.assertEqual(app.get_programacoes(), [])

        app.save_programacao({"numero_pedido": "123", "motorista": "Ana"})
        self.assertEqual(app.get_programacoes()[-1]["numero_pedido"], "123")


if __name__ == "__main__":
    unittest.main()
