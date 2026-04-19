from flask import Blueprint
from flask_login import login_required
from flask import render_template
from .models import User
from . import views

views = Blueprint('views', __name__)

from .models import (
    User,
    GroupPrediction,
    RealGroupMatchResult,
    KnockoutPrediction,
    RealKnockoutResult,
    StatisticsPrediction,
    RealStatisticsResult
)

from flask import redirect, url_for
from flask_login import logout_user, login_required

@views.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("routes.login"))


def compute_group_points(user):
    points = 0

    for pred in user.group_predictions:
        real = RealGroupMatchResult.query.filter_by(match_id=pred.match_id).first()
        if not real:
            continue

        # Exact result
        if pred.goals_team1 == real.goals_team1 and pred.goals_team2 == real.goals_team2:
            points += 2
        else:
            # Correct outcome (win/draw)
            pred_diff = pred.goals_team1 - pred.goals_team2
            real_diff = real.goals_team1 - real.goals_team2

            if (pred_diff > 0 and real_diff > 0) or \
               (pred_diff < 0 and real_diff < 0) or \
               (pred_diff == 0 and real_diff == 0):
                points += 1

    return points


def compute_knockout_points(user):
    points = 0

    for pred in user.knockout_predictions:
        real = RealKnockoutResult.query.filter_by(team_id=pred.team_id).first()
        if not real:
            continue

        if pred.eliminated_round == real.eliminated_round:
            if real.eliminated_round == "WINNER":
                points += 50
            else:
                points += 5

    return points


def compute_statistics_points(user):
    real = RealStatisticsResult.query.first()
    pred = user.statistics_prediction[0] if user.statistics_prediction else None

    if not real or not pred:
        return 0

    points = 0

    fields = [
        "best_player",
        "second_best_player",
        "third_best_player",
        "best_young_player",
        "best_goalkeeper",
        "top_scorer",
        "top_assister"
    ]

    for field in fields:
        if getattr(pred, field) == getattr(real, field):
            points += 10

    return points


def compute_total_points(user):
    return (
        compute_group_points(user)
        + compute_knockout_points(user)
        + compute_statistics_points(user)
    )


@views.route("/", methods=["GET"])
@login_required
def home():
    users = User.query.all()
    leaderboard = []

    for user in users:
        # 🚫 Skip incomplete profiles
        if not user.name or not user.school_level or not user.favorite_team:
            continue

        leaderboard.append({
            "id": user.id,
            "name": user.name,
            "school_level": user.school_level,
            "favorite_team": user.favorite_team,
            "points": compute_total_points(user)
        })

    leaderboard.sort(key=lambda x: x["points"], reverse=True)

    return render_template("home.html", leaderboard=leaderboard)
