from servidor.mapeador_palma import MapeadorPalma
from servidor.rastreador_mano import RastreadorMano


def test_normalizar_lado_mano_usa_nombres_de_palma():
    assert MapeadorPalma._normalizar_lado_mano({"lado": "left"}) == "palma derecha"
    assert MapeadorPalma._normalizar_lado_mano({"lado": "right"}) == "palma izquierda"
    assert MapeadorPalma._normalizar_lado_mano({"lado": "palma izquierda"}) == "palma izquierda"


def test_normalizar_lado_del_rastreador_usa_nombres_de_palma():
    assert RastreadorMano._normalizar_lado("left") == "palma izquierda"
    assert RastreadorMano._normalizar_lado("right") == "palma derecha"
