import tempfile
import unittest
from pathlib import Path

from servidor.aplicacion import listar_capturas


class TestListarCapturas(unittest.TestCase):
    def test_listar_capturas_incluye_archivos_png(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            import servidor.aplicacion as aplicacion

            original = aplicacion.DIRECTORIO_CAPTURAS
            try:
                aplicacion.DIRECTORIO_CAPTURAS = tmp_path

                (tmp_path / "captura-1.png").write_bytes(b"png")
                (tmp_path / "captura-2.jpg").write_bytes(b"jpg")

                datos = listar_capturas()
                urls = [captura["url"] for captura in datos["capturas"]]

                self.assertIn("/capturas/captura-1.png", urls)
                self.assertIn("/capturas/captura-2.jpg", urls)
            finally:
                aplicacion.DIRECTORIO_CAPTURAS = original

    def test_eliminar_captura_reinicia_numeracion_siguiente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            import servidor.aplicacion as aplicacion

            original = aplicacion.DIRECTORIO_CAPTURAS
            try:
                aplicacion.DIRECTORIO_CAPTURAS = tmp_path

                (tmp_path / "graciasporvenir001.png").write_bytes(b"png")
                (tmp_path / "graciasporvenir002.png").write_bytes(b"png")

                aplicacion.eliminar_captura("graciasporvenir002.png")

                self.assertFalse((tmp_path / "graciasporvenir002.png").exists())
                self.assertEqual(aplicacion._generar_nombre_captura("png"), "graciasporvenir002.png")
            finally:
                aplicacion.DIRECTORIO_CAPTURAS = original
