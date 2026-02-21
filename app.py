from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        try:
            loc = float(request.form["loc"])
            cost_per_dev = float(request.form["cost"])

            # Validation (NFR-01 Accuracy + NFR-04 Scalability)
            if loc <= 0 or cost_per_dev <= 0:
                error = "Please enter valid positive numbers."
            else:
                kloc = loc / 1000  # Convert LOC to KLOC

                # Basic COCOMO (Organic Mode)
                a = 2.4
                b = 1.05

                effort = a * (kloc ** b)         # FR-04, FR-05
                time = 2.5 * (effort ** 0.38)   # FR-06, FR-07
                total_cost = effort * cost_per_dev  # FR-02, FR-03

                result = {
                    "effort": round(effort, 2),
                    "time": round(time, 2),
                    "cost": round(total_cost, 2)
                }

        except:
            error = "Invalid input. Please enter numeric values only."

    return render_template("index.html", result=result, error=error)

if __name__ == "__main__":
    app.run(debug=True)