import pandas as pd
import re

# اسم ملف SCATS الذي سنقرأه
file_name = "wadi_saqra_scats.txt"

records = []

current_detector = None

with open(file_name, "r") as file:
    for line in file:

        line = line.strip()

        if not line:
            continue

        # إذا وجد Detector جديد
        if line.startswith("Detector"):

            current_detector = line.split()[1]
            continue

        # قراءة التاريخ والوقت وعدد السيارات
        match = re.match(
            r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) (\d+)",
            line
        )

        if match:

            date = match.group(1)
            time = match.group(2)
            count = int(match.group(3))

            records.append({
                "timestamp": f"{date} {time}",
                "detector_id": current_detector,
                "vehicle_count": count
            })

df = pd.DataFrame(records)

print(df.head())

df.to_csv("parsed_scats.csv", index=False)

print("Finished Successfully!")