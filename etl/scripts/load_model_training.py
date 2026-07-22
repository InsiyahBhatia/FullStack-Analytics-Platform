"""Load model training metadata into fact_model_training."""
import json
import os
import glob
import psycopg2

DB = dict(host="localhost", port=5433, dbname="finsight", user="finsight_user", password="finsight_dev_2026")
ARTIFACTS = os.path.join(os.path.dirname(__file__), "..", "..", "models", "artifacts")

def load():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM fact_model_training")
    for path in glob.glob(os.path.join(ARTIFACTS, "*_metadata.json")):
        with open(path) as f:
            m = json.load(f)
        cur.execute(
            """INSERT INTO fact_model_training
               (model_name, task, algorithm, version, accuracy, precision_score,
                recall_score, f1_score, roc_auc, threshold, training_seconds, features, target)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (m["name"], m["task"], m["algorithm"], m["version"],
             m["metrics"]["accuracy"], m["metrics"]["precision"],
             m["metrics"]["recall"], m["metrics"]["f1"], m["metrics"]["roc_auc"],
             m["threshold"], m["metrics"]["training_seconds"],
             json.dumps(m["features"]), m["target"])
        )
        print(f"  loaded {m['name']}")
    conn.commit()
    cur.close()
    conn.close()
    print("Done")

if __name__ == "__main__":
    load()
