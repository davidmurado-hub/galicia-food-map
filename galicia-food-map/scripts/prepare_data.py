"""Prepara los puntos reales de OpenStreetMap para Galicia Food Map.

Uso en PowerShell, dentro de la carpeta del proyecto:
    python scripts/prepare_data.py

Si Overpass está saturado, en https://overpass-turbo.eu/ ejecuta la consulta
contenida en overpass.txt y exporta en formato GeoJSON o JSON bruto. Luego:
    python scripts/prepare_data.py --importar data/raw/restaurantes.geojson data/raw/kebabs.geojson

No necesita paquetes externos. No inventa ningún restaurante.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESTINO = ROOT / "data" / "puntos_osm.js"
SERVIDORES = (
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
CABECERAS = {
    "User-Agent": "GaliciaFoodMap/1.0 (descarga puntual OpenStreetMap)",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Accept": "application/json",
}


def centro_geometria(geometria):
    """Coordenadas lon/lat del centro aproximado de una geometría GeoJSON.

    Para Point usa el punto exacto; para polígonos o líneas usa el promedio
    de vértices (aproximación suficiente para situar el marcador del local).
    """
    if not isinstance(geometria, dict):
        return None
    tipo = geometria.get("type")
    coords = geometria.get("coordinates")
    if tipo == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
        return coords[:2]

    puntos = []
    def recorrer(valor):
        if isinstance(valor, (list, tuple)):
            if len(valor) >= 2 and all(isinstance(x, (float, int)) for x in valor[:2]):
                puntos.append((valor[0], valor[1]))
            else:
                for x in valor:
                    recorrer(x)
    recorrer(coords)
    if not puntos:
        return None
    # En anillos cerrados, el primer punto suele estar repetido al final.
    if len(puntos) >= 4 and puntos[0] == puntos[-1]:
        puntos.pop()
    return [sum(x for x, _ in puntos) / len(puntos),
            sum(y for _, y in puntos) / len(puntos)]


def geojson_a_elementos(geojson):
    """Convierte un GeoJSON de Overpass Turbo a elementos OSM para mapa.js."""
    if geojson.get("type") == "Feature":
        features = [geojson]
    else:
        features = geojson.get("features", [])
    elementos = []
    for i, feature in enumerate(features):
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        if not isinstance(props, dict):
            continue
        ident = (props.get("@id") or feature.get("id") or props.get("id"))
        # El ID de Overpass Turbo suele ser "node/123", "way/123"...
        tipo = None
        numero = None
        if isinstance(ident, str):
            match = re.search(r"(node|way|relation)/(\d+)", ident)
            if match:
                tipo, numero = match.group(1), int(match.group(2))
        elif isinstance(ident, (int, float)):
            tipo, numero = "node", int(ident)
        if tipo is None:
            # ID sintético estable, solo para que el mapa admita el punto.
            # Estos registros no se atribuyen falsamente a un ID OSM.
            import hashlib
            huella = json.dumps([props, feature.get("geometry")], ensure_ascii=False,
                                 sort_keys=True).encode("utf-8")
            tipo = "geojson"
            numero = int(hashlib.sha1(huella).hexdigest()[:14], 16)
        lonlat = centro_geometria(feature.get("geometry"))
        if lonlat is None:
            continue
        lon, lat = lonlat
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue
        tags = props.get("tags") if isinstance(props.get("tags"), dict) else {
            clave: valor for clave, valor in props.items()
            if not clave.startswith("@") and clave not in ("id", "tags")
        }
        elementos.append({"type": tipo, "id": numero, "lat": lat, "lon": lon,
                          "tags": tags})
    return elementos


def obtener_elementos(respuesta):
    """Acepta GeoJSON (FeatureCollection) y JSON bruto de Overpass."""
    if not isinstance(respuesta, dict):
        raise ValueError("El contenido debe ser un objeto JSON o GeoJSON.")
    if isinstance(respuesta.get("elements"), list):
        elementos = respuesta["elements"]
    elif respuesta.get("type") in ("FeatureCollection", "Feature"):
        elementos = geojson_a_elementos(respuesta)
    else:
        raise ValueError("Formato no reconocido. Exporta GeoJSON o datos brutos JSON desde Overpass Turbo.")
    if not elementos:
        raise ValueError("No se encontraron elementos con coordenadas; no se guardará un archivo vacío.")
    return elementos


def elementos_guardados():
    """Permite añadir exportaciones separadas sin perder las anteriores."""
    if not DESTINO.is_file():
        return []
    contenido = DESTINO.read_text(encoding="utf-8")
    match = re.search(r"window\.OSM_ELEMENTOS\s*=\s*(\[.*?\]|null)\s*;", contenido, re.S)
    if not match or match.group(1) == "null":
        return []
    try:
        datos = json.loads(match.group(1))
        return datos if isinstance(datos, list) else []
    except json.JSONDecodeError:
        return []


def combinar_elementos(*conjuntos):
    """Une resultados de distintas consultas sin duplicar ID de OSM."""
    por_id = {}
    for conjunto in conjuntos:
        for e in conjunto:
            if isinstance(e, dict) and "id" in e and "type" in e:
                por_id[f"{e['type']}/{e['id']}"] = e
    return list(por_id.values())


def guardar_elementos(elementos, origen, acumular=False):
    if acumular:
        elementos = combinar_elementos(elementos_guardados(), elementos)
    else:
        elementos = combinar_elementos(elementos)
    if not elementos:
        raise ValueError("No hay puntos OSM válidos que guardar.")
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    contenido = (
        "// Puntos reales de OpenStreetMap. Consultas en overpass.txt o consulta_*.txt.\n"
        "// Origen: " + origen + "\n"
        "window.OSM_ELEMENTOS = "
        + json.dumps(elementos, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    temporal = DESTINO.with_suffix(".js.tmp")
    temporal.write_text(contenido, encoding="utf-8")
    temporal.replace(DESTINO)
    print(f"CORRECTO: {len(elementos)} elementos OSM guardados en {DESTINO.relative_to(ROOT)}")
    print("Abre index.html y activa las capas 2 o 3.")

def descargar_puntos():
    query = (ROOT / "queries" / "overpass.txt").read_text(encoding="utf-8")
    payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
    errores = []
    for servidor in SERVIDORES:
        print(f"Probando servidor: {servidor}", flush=True)
        try:
            peticion = urllib.request.Request(
                servidor, data=payload, method="POST", headers=CABECERAS
            )
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                datos = json.load(respuesta)
            elementos = obtener_elementos(datos)
            guardar_elementos(elementos, servidor)
            return True
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError,
                ValueError, OSError) as exc:
            errores.append(f"{servidor}: {exc}")
            print(f"  Falló: {exc}", flush=True)
    print("\nERROR: Ninguno de los servidores ha respondido correctamente.")
    print("Puedes descargar los datos (GeoJSON o JSON bruto) desde https://overpass-turbo.eu/")
    print("utilizando overpass.txt y después ejecutar:")
    print('  python scripts/prepare_data.py --importar "RUTA_AL_ARCHIVO_DESCARGADO"')
    print("No se han borrado datos guardados anteriormente.")
    return False


def importar_json(rutas):
    """Importa uno o varios JSON/GeoJSON; conserva los anteriores."""
    nuevos = []
    for ruta_str in rutas:
        ruta = Path(ruta_str).expanduser()
        try:
            with ruta.open(encoding="utf-8-sig") as archivo:
                respuesta = json.load(archivo)
            elementos = obtener_elementos(respuesta)
            nuevos.extend(elementos)
            print(f"Importados {len(elementos)} elementos de {ruta.name}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR al importar {ruta}: {exc}")
            return False
    try:
        guardar_elementos(nuevos, "exportación manual JSON/GeoJSON de Overpass Turbo", acumular=True)
        return True
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return False

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--importar", nargs="+", metavar="ARCHIVO.json|.geojson", help="Archivos JSON brutos o GeoJSON exportados por Overpass Turbo")
    args = parser.parse_args()
    exito = importar_json(args.importar) if args.importar else descargar_puntos()
    if not exito:
        sys.exit(1)
    print("\nPreparación terminada. Comprueba el mapa abriendo index.html.")


if __name__ == "__main__":
    main()
