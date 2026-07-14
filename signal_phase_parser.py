import pandas as pd


file_name = "signal_phase_log.txt"

records = []


# قراءة ملف الإشارات
with open(file_name, "r") as file:
    for line in file:

        line = line.strip()

        if not line:
            continue

        parts = line.split(",")

        timestamp = parts[0]
        intersection_id = parts[1]
        phase_number = parts[2]
        light_state = parts[3]

        records.append({
            "timestamp": timestamp,
            "intersection_id": intersection_id,
            "phase_number": phase_number,
            "light_state": light_state
        })


df = pd.DataFrame(records)

# تحويل الوقت إلى datetime
df["timestamp"] = pd.to_datetime(df["timestamp"])


# حساب مدة اللون الأخضر
green_durations = []

for phase in df["phase_number"].unique():

    phase_data = df[df["phase_number"] == phase]

    green_start = None

    for _, row in phase_data.iterrows():

        if row["light_state"] == "GREEN":
            green_start = row["timestamp"]

        elif row["light_state"] == "YELLOW" and green_start:
            duration = (
                row["timestamp"] - green_start
            ).seconds

            green_durations.append({
                "phase_number": phase,
                "green_duration_seconds": duration
            })

            green_start = None


duration_df = pd.DataFrame(green_durations)


print(df)

print("\nGreen Duration:")
print(duration_df)


df.to_csv("parsed_signal_phase.csv", index=False)

duration_df.to_csv(
    "green_duration.csv",
    index=False
)


print("\nFinished Successfully!")