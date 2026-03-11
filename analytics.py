import matplotlib.pyplot as plt
from database import connect

def seizure_trends():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT date FROM seizures")

    data = cursor.fetchall()

    counts = {}

    for d in data:

        date = d[0]

        if date in counts:
            counts[date] += 1
        else:
            counts[date] = 1

    x = list(counts.keys())
    y = list(counts.values())

    plt.plot(x, y, marker="o")

    plt.title("Seizure Trends")
    plt.xlabel("Date")
    plt.ylabel("Seizure Count")

    plt.xticks(rotation=45)

    plt.show()