"""Détection d'éoliennes sur images satellite via YOLOv11.

Usage:
    python ml/yolo_detection.py --image data/sample/sentinel2_60.tif
    python ml/yolo_detection.py --image tile.jpg --model models/yolo11_eoliennes.pt
    python ml/yolo_detection.py --tile-dir data/tiles/ --output results/detections.geojson
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, box

MODEL_PATH = Path("ml/models/yolo11_eoliennes.pt")
CONFIDENCE_THRESHOLD = 0.35
TILE_SIZE = 640  # pixels


def load_model(model_path: str = str(MODEL_PATH)):
    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        return model
    except ImportError:
        raise ImportError("ultralytics requis : pip install ultralytics")


def detect_on_tile(model, tile_path: str, conf: float = CONFIDENCE_THRESHOLD) -> list[dict]:
    results = model(tile_path, conf=conf, verbose=False)
    detections = []
    for result in results:
        for box_data in result.boxes:
            x1, y1, x2, y2 = box_data.xyxy[0].tolist()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            detections.append({
                "x_pixel": cx,
                "y_pixel": cy,
                "confidence": float(box_data.conf[0]),
                "bbox": [x1, y1, x2, y2],
                "tile": str(tile_path),
            })
    return detections


def pixel_to_geo(x_pixel: float, y_pixel: float, transform) -> tuple[float, float]:
    """Convertit coordonnées pixel → coordonnées géographiques (affine transform)."""
    lon = transform.c + x_pixel * transform.a
    lat = transform.f + y_pixel * transform.e
    return lon, lat


def detect_on_raster(raster_path: str, model_path: str = str(MODEL_PATH), output_path: str | None = None) -> gpd.GeoDataFrame:
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError:
        raise ImportError("rasterio requis : pip install rasterio")

    model = load_model(model_path)
    all_detections = []

    with rasterio.open(raster_path) as src:
        transform = src.transform
        width, height = src.width, src.height

        for y_off in range(0, height, TILE_SIZE):
            for x_off in range(0, width, TILE_SIZE):
                window = Window(x_off, y_off, min(TILE_SIZE, width - x_off), min(TILE_SIZE, height - y_off))
                data = src.read([1, 2, 3], window=window)
                tile_img = np.transpose(data, (1, 2, 0))

                detections = detect_on_tile(model, tile_img)
                for det in detections:
                    geo_x, geo_y = pixel_to_geo(
                        det["x_pixel"] + x_off,
                        det["y_pixel"] + y_off,
                        transform,
                    )
                    det["geometry"] = Point(geo_x, geo_y)
                    det["crs"] = str(src.crs)
                    all_detections.append(det)

    gdf = gpd.GeoDataFrame(all_detections, crs=src.crs)
    gdf = gdf.to_crs(epsg=2154)
    gdf["source_image"] = raster_path

    if output_path:
        gdf.to_file(output_path, driver="GeoJSON")
        print(f"{len(gdf)} éoliennes détectées → {output_path}")

    return gdf


def compute_metrics(gdf_pred: gpd.GeoDataFrame, gdf_truth: gpd.GeoDataFrame, buffer_m: float = 100.0) -> dict:
    """Évalue la précision de la détection par buffer matching."""
    gdf_pred_buf = gdf_pred.copy()
    gdf_pred_buf["geometry"] = gdf_pred.geometry.buffer(buffer_m)
    joined = gpd.sjoin(gdf_truth, gdf_pred_buf, how="left", predicate="within")
    tp = joined["index_right"].notna().sum()
    fp = len(gdf_pred) - tp
    fn = joined["index_right"].isna().sum()
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3), "tp": int(tp), "fp": int(fp), "fn": int(fn)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Détection éoliennes YOLOv11 sur images satellite")
    parser.add_argument("--image", help="Chemin image raster (GeoTIFF)")
    parser.add_argument("--model", default=str(MODEL_PATH))
    parser.add_argument("--output", default="results/detections.geojson")
    parser.add_argument("--conf", type=float, default=CONFIDENCE_THRESHOLD)
    args = parser.parse_args()

    if args.image:
        gdf = detect_on_raster(args.image, model_path=args.model, output_path=args.output)
        print(f"Détections : {len(gdf)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
