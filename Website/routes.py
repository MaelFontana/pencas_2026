from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user
from .models import AccessCredential, User
from . import db
import secrets, hashlib
import smtplib
from flask_login import login_required, current_user
from .models import Group, GroupMatch, GroupPrediction, KnockoutPrediction, StatisticsPrediction, AdminConfig, Team, RealGroupMatchResult, RealKnockoutResult
from collections import defaultdict
import random
from .data.players import PLAYERS
from werkzeug.security import generate_password_hash, check_password_hash
from .models import RealStatisticsResult

routes = Blueprint('routes', __name__)

SERVER_SECRET = "oijeiheiuh874y98743g"

def make_hash(public_id, password):
    raw = f"{public_id}:{password}:{SERVER_SECRET}"
    return hashlib.sha256(raw.encode()).hexdigest()

def generate_credential():
    public_id = "WC26-" + secrets.token_hex(3).upper()
    password = secrets.token_hex(4).upper()
    raw = f"{public_id}:{password}:{SERVER_SECRET}"
    secret_hash = hashlib.sha256(raw.encode()).hexdigest()
    return public_id, password, secret_hash

@routes.route('/generate-credentials')
def generate_credentials():
    generated = []

    for _ in range(10):
        pid, pwd, h = generate_credential()
        db.session.add(AccessCredential(public_id=pid, secret_hash=h))
        generated.append({"id": pid, "password": pwd})

    db.session.commit()
    return {"generated": generated}

def send_credentials_email(credentials):
    fromaddress = "glolibros.jules.supervielle@gmail.com"
    toaddress = "mael.fontana.allain@gmail.com"

    body = "PENCA MUNDIAL 2026  CREDENTIALS\n\n"
    for pid, pwd in credentials:
        body += f"ID: {pid} | PASSWORD: {pwd}\n"

    message = f"Subject: Penca Mundial 2026  Credenciales\n\n{body}"

    with smtplib.SMTP("smtp.gmail.com", 587) as smtpserver:
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo()
        smtpserver.login(fromaddress,'oyri izmn votv nuar')
        smtpserver.sendmail(fromaddress, toaddress, message)

def compute_group_standings(user):
    groups = Group.query.all()
    group_results = {}
    third_places = []

    for group in groups:
        table = {}

        # init teams
        for team in group.teams:
            table[team.id] = {
                "team": team,
                "points": 0,
                "gf": 0,
                "ga": 0,
                "gd": 0
            }

        # process matches
        for match in group.matches:
            pred = GroupPrediction.query.filter_by(
                user_id=user.id,
                match_id=match.id
            ).first()

            if not pred:
                continue  # safety

            t1 = table[match.team1_id]
            t2 = table[match.team2_id]

            g1 = pred.goals_team1
            g2 = pred.goals_team2

            t1["gf"] += g1
            t1["ga"] += g2
            t2["gf"] += g2
            t2["ga"] += g1

            if g1 > g2:
                t1["points"] += 3
            elif g2 > g1:
                t2["points"] += 3
            else:
                t1["points"] += 1
                t2["points"] += 1

        for t in table.values():
            t["gd"] = t["gf"] - t["ga"]

        ordered = sorted(
            table.values(),
            key=lambda x: (x["points"], x["gd"], x["gf"]),
            reverse=True
        )

        group_results[group.name] = {
            "first": ordered[0],
            "second": ordered[1],
            "third": ordered[2]
        }

        third_places.append(ordered[2])

    # best 8 third places
    best_thirds = sorted(
        third_places,
        key=lambda x: (x["points"], x["gd"], x["gf"]),
        reverse=True
    )[:8]

    return group_results, best_thirds

def generate_third_place_mapping(winners, best_thirds):
    """
    winners: dict { group_letter: team_obj }
    best_thirds: list of third-place dicts already sorted
    """

    mapping = {}
    used_thirds = set()

    # Order winners A → L (FIFA seeding)
    ordered_winners = sorted(winners.keys())

    for w_group in ordered_winners:
        for third in best_thirds:
            t_group = third["team"].group.name

            if t_group == w_group:
                continue

            if t_group in used_thirds:
                continue

            mapping[w_group] = t_group
            used_thirds.add(t_group)
            break

    return mapping

def predictions_are_locked():
    return (
        RealGroupMatchResult.query.first() is not None
        or RealKnockoutResult.query.first() is not None
        or RealStatisticsResult.query.first() is not None
    )


@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        public_id = request.form['public_id']
        password = request.form['password']

        credential = AccessCredential.query.filter_by(public_id=public_id).first()
        if not credential:
            flash("Credenciales inválidos")
            return redirect(url_for('routes.login'))

        if make_hash(public_id, password) != credential.secret_hash:
            flash("Credenciales inválidos")
            return redirect(url_for('routes.login'))

        # Credential already used → existing user
        if credential.is_used:
            user = User.query.filter_by(access_credential_id=credential.id).first()
            login_user(user)

            if predictions_are_locked():
                return redirect(url_for('views.home'))

            return redirect(url_for('routes.complete_profile'))

        # New user
        user = User(
            name="",
            favorite_team="",
            school_level="",
            access_credential_id=credential.id
        )

        credential.is_used = True
        db.session.add(user)
        db.session.commit()

        login_user(user)

        if predictions_are_locked():
            return redirect(url_for('views.home'))

        return redirect(url_for('routes.complete_profile'))

    return render_template('login.html')


@routes.route("/complete-profile", methods=["GET", "POST"])
@login_required
def complete_profile():
    if request.method == "POST":
        name = request.form.get("name").strip()
        level = request.form.get("level")
        country = request.form.get("country").strip()

        if not name or not level or not country:
            return render_template(
                "complete_profile.html",
                error="Todos los campos son obligatorios."
            )

        current_user.name = name
        current_user.school_level = level
        current_user.favorite_team = country
        current_user.has_completed_profile = True

        db.session.commit()

        return redirect(url_for("routes.group_phase"))

    return render_template("complete_profile.html")


@routes.route("/group-phase", methods=["GET", "POST"])
@login_required
def group_phase():
    if predictions_are_locked():
        flash("Las predicciones ya están cerradas.")
        return redirect(url_for("views.home"))
    if current_user.has_predicted_groups:
        flash("Ya completaste esta fase.")
        return redirect(url_for("views.home"))

    groups = Group.query.order_by(Group.name).all()

    if request.method == "POST":
        for group in groups:
            for match in group.matches:
                g1 = request.form.get(f"m{match.id}_1")
                g2 = request.form.get(f"m{match.id}_2")

                if g1 is None or g2 is None:
                    flash("Tenés que completar todos los partidos.")
                    return redirect(url_for("routes.group_phase"))

                prediction = GroupPrediction(
                    user_id=current_user.id,
                    match_id=match.id,
                    goals_team1=int(g1),
                    goals_team2=int(g2)
                )
                db.session.add(prediction)

        current_user.has_predicted_groups = True
        db.session.commit()

        return redirect(url_for("routes.knockout"))

    return render_template("group_phase.html", groups=groups)


@routes.route("/knockout", methods=["GET"])
@login_required
def knockout():
    if predictions_are_locked():
        flash("Las predicciones ya están cerradas.")
        return redirect(url_for("views.home"))
    group_results, best_thirds = compute_group_standings(current_user)

    # 1. Map winners (1st) and runners-up (2nd)
    w = {g: r["first"]["team"] for g, r in group_results.items()}
    r = {g: r["second"]["team"] for g, r in group_results.items()}
    
    # 2. Extract top 8 thirds and shuffle
    thirds = [t["team"] for t in best_thirds[:8]]
    random.shuffle(thirds)

    # 3. Official FIFA 2026 Bracket Mapping
    # Organized so winners meet in Semi-finals: (Match 97 vs 98) and (Match 99 vs 100)
    bracket = {
        "round_of_32": {
            "A": [
                # --- Path to Quarter-final Match 97 (Winner 89 v 90) ---
                {"team1": w['E'], "team2": thirds[0]},   # Match 74
                {"team1": w['I'], "team2": thirds[1]},   # Match 77 -> Winner 89
                {"team1": r['A'], "team2": r['B']},      # Match 73
                {"team1": w['F'], "team2": r['C']},      # Match 75 -> Winner 90
                
                # --- Path to Quarter-final Match 98 (Winner 93 v 94) ---
                {"team1": r['K'], "team2": r['L']},      # Match 83
                {"team1": w['H'], "team2": r['J']},      # Match 84 -> Winner 93
                {"team1": w['D'], "team2": thirds[4]},   # Match 81
                {"team1": w['G'], "team2": thirds[5]},   # Match 82 -> Winner 94
                # WINNER 97 vs WINNER 98 = SEMIFINAL 1 (July 14, Dallas)
            ],
            "B": [
                # --- Path to Quarter-final Match 99 (Winner 91 v 92) ---
                {"team1": w['C'], "team2": r['F']},      # Match 76
                {"team1": r['E'], "team2": r['I']},      # Match 78 -> Winner 91
                {"team1": w['A'], "team2": thirds[2]},   # Match 79
                {"team1": w['L'], "team2": thirds[3]},   # Match 80 -> Winner 92
                
                # --- Path to Quarter-final Match 100 (Winner 95 v 96) ---
                {"team1": w['J'], "team2": r['H']},      # Match 86
                {"team1": r['D'], "team2": r['G']},      # Match 88 -> Winner 95
                {"team1": w['B'], "team2": thirds[6]},   # Match 85
                {"team1": w['K'], "team2": thirds[7]},   # Match 87 -> Winner 96
                # WINNER 99 vs WINNER 100 = SEMIFINAL 2 (July 15, Atlanta)
            ]
        }
    }

    return render_template("knockout.html", bracket=bracket)


@routes.route("/submit-knockout", methods=["POST"])
@login_required
def submit_knockout():
    data = request.get_json()

    KnockoutPrediction.query.filter_by(
        user_id=current_user.id
    ).delete()

    def save(team_ids, round_name):
        for team_id in team_ids:
            db.session.add(KnockoutPrediction(
                user_id=current_user.id,
                team_id=team_id,
                eliminated_round=round_name
            ))

    save(data["R32"], "R32")
    save(data["R16"], "R16")
    save(data["QF"],  "QF")
    save(data["SF"],  "SF")

    db.session.add(KnockoutPrediction(
        user_id=current_user.id,
        team_id=data["RUNNER_UP"],
        eliminated_round="FINAL"
    ))

    db.session.add(KnockoutPrediction(
        user_id=current_user.id,
        team_id=data["WINNER"],
        eliminated_round="WINNER"
    ))

    db.session.commit()
    return {"status": "ok"}


@routes.route("/predict-statistics", methods=["GET", "POST"])
@login_required
def predict_statistics():
    if predictions_are_locked():
        flash("Las predicciones ya están cerradas.")
        return redirect(url_for("views.home"))
    existing = StatisticsPrediction.query.filter_by(
        user_id=current_user.id
    ).first()

    if request.method == "POST":
        if existing:
            db.session.delete(existing)

        prediction = StatisticsPrediction(
            user_id=current_user.id,
            best_player=request.form["best_player"],
            second_best_player=request.form["second_best_player"],
            third_best_player=request.form["third_best_player"],
            best_young_player=request.form["best_young_player"],
            best_goalkeeper=request.form["best_goalkeeper"],
            top_scorer=request.form["top_scorer"],
            top_assister=request.form["top_assister"]
        )

        db.session.add(prediction)
        db.session.commit()

        return redirect(url_for("views.home"))  # or next step

    return render_template(
        "statistics.html",
        players=PLAYERS
    )


@routes.route("/secret-admin-2026", methods=["GET", "POST"])
def secret_admin():
    admin = AdminConfig.query.first()

    # Create row if it doesn't exist
    if not admin:
        admin = AdminConfig()
        db.session.add(admin)
        db.session.commit()

    # -------------------------
    # FIRST TIME: CREATE PASSWORD
    # -------------------------
    if not admin.initialized:
        if request.method == "POST":
            password = request.form.get("password")
            confirm = request.form.get("confirm")

            if password != confirm:
                flash("Passwords do not match", "danger")
                return redirect(url_for("routes.secret_admin"))

            admin.admin_password_hash = generate_password_hash(password)
            admin.initialized = True
            db.session.commit()

            session["is_admin"] = True
            flash("Admin password created", "success")
            return redirect(url_for("routes.secret_admin"))

        return render_template("admin_create_password.html")

    # -------------------------
    # NORMAL LOGIN
    # -------------------------
    if not session.get("is_admin"):
        if request.method == "POST":
            password = request.form.get("password")

            if not check_password_hash(admin.admin_password_hash, password):
                flash("Wrong password", "danger")
                return redirect(url_for("routes.secret_admin"))

            session["is_admin"] = True
            return redirect(url_for("routes.secret_admin"))

        return render_template("admin_login.html")

    # -------------------------
    # ADMIN PANEL
    # -------------------------
    matches = GroupMatch.query.all()
    teams = Team.query.order_by(Team.name).all()

    group_results = {
        r.match_id: r
        for r in RealGroupMatchResult.query.all()
    }

    knockout_results = {
        r.team_id: r
        for r in RealKnockoutResult.query.all()
    }

    real_statistics = RealStatisticsResult.query.first()

    return render_template(
        "secret.html",
        matches=matches,
        teams=teams,
        group_results=group_results,
        knockout_results=knockout_results,
        real_statistics=real_statistics,
        players=PLAYERS
    )



@routes.route("/secret-admin-2026/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("routes.secret_admin"))


@routes.route("/secret-admin-2026/save-group-results", methods=["POST"])
def save_group_results():
    if not session.get("is_admin"):
        return redirect(url_for("routes.secret_admin"))

    from .models import RealGroupMatchResult, GroupMatch

    matches = GroupMatch.query.all()

    for match in matches:
        # If result already exists → DO NOTHING
        existing = RealGroupMatchResult.query.filter_by(match_id=match.id).first()
        if existing:
            continue

        g1 = request.form.get(f"g1_{match.id}")
        g2 = request.form.get(f"g2_{match.id}")

        if g1 in (None, "") or g2 in (None, ""):
            continue

        real = RealGroupMatchResult(
            match_id=match.id,
            goals_team1=int(g1),
            goals_team2=int(g2)
        )
        db.session.add(real)

    db.session.commit()
    flash("Group match results saved (locked)", "success")
    return redirect(url_for("routes.secret_admin"))


@routes.route("/secret-admin-2026/save-knockout-results", methods=["POST"])
def save_knockout_results():
    if not session.get("is_admin"):
        return redirect(url_for("routes.secret_admin"))

    from .models import RealKnockoutResult, Team

    teams = Team.query.all()

    for team in teams:
        existing = RealKnockoutResult.query.filter_by(team_id=team.id).first()
        if existing:
            continue

        round_eliminated = request.form.get(f"round_{team.id}")
        if not round_eliminated:
            continue

        real = RealKnockoutResult(
            team_id=team.id,
            eliminated_round=round_eliminated
        )
        db.session.add(real)

    db.session.commit()
    flash("Knockout eliminations saved (locked)", "success")
    return redirect(url_for("routes.secret_admin"))


@routes.route("/secret-admin-2026/save-statistics-results", methods=["POST"])
def save_statistics_results():
    if not session.get("is_admin"):
        return redirect(url_for("routes.secret_admin"))

    real = RealStatisticsResult.query.first()

    fields = [
        "best_player",
        "second_best_player",
        "third_best_player",
        "best_young_player",
        "best_goalkeeper",
        "top_scorer",
        "top_assister"
    ]

    # If no row yet → create empty one
    if not real:
        real = RealStatisticsResult(
            best_player="",
            second_best_player="",
            third_best_player="",
            best_young_player="",
            best_goalkeeper="",
            top_scorer="",
            top_assister=""
        )
        db.session.add(real)
        db.session.commit()

    updated = False

    for field in fields:
        current_value = getattr(real, field)
        new_value = request.form.get(field)

        # Only fill if empty AND provided
        if not current_value and new_value:
            setattr(real, field, new_value)
            updated = True

    if updated:
        db.session.commit()
        flash("Individual awards updated (locked per field)", "success")

    return redirect(url_for("routes.secret_admin"))
