from . import db
from flask_login import UserMixin
from datetime import datetime

# -------------------------
# AUTH / SYSTEM
# -------------------------

class AccessCredential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(20), unique=True, nullable=False)
    secret_hash = db.Column(db.String(256), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=True)
    name = db.Column(db.String(100), nullable=True)
    favorite_team = db.Column(db.String(50), nullable=True)
    school_level = db.Column(db.String(50), nullable=True)

    has_completed_profile = db.Column(db.Boolean, default=False)
    has_predicted_groups = db.Column(db.Boolean, default=False)

    access_credential_id = db.Column(
        db.Integer,
        db.ForeignKey('access_credential.id'),
        unique=True,
        nullable=False
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    access_credential = db.relationship(
        'AccessCredential',
        backref=db.backref('user', uselist=False)
    )


class SystemState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credentials_generated = db.Column(db.Boolean, default=False)

# -------------------------
# WORLD CUP STRUCTURE
# -------------------------

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1), nullable=False)

    matches = db.relationship(
        'GroupMatch',
        back_populates='group',
        lazy=True
    )

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)

    group = db.relationship('Group', backref='teams')


class GroupMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)

    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

    group = db.relationship(
        'Group',
        back_populates='matches'
    )

    team1 = db.relationship('Team', foreign_keys=[team1_id])
    team2 = db.relationship('Team', foreign_keys=[team2_id])


class GroupPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('group_match.id'), nullable=False)

    goals_team1 = db.Column(db.Integer, nullable=False)
    goals_team2 = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='group_predictions')
    match = db.relationship('GroupMatch')


class KnockoutPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False)

    # R32, R16, QF, SF, FINAL, WINNER
    eliminated_round = db.Column(db.String(10), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="knockout_predictions")
    team = db.relationship("Team")


class StatisticsPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    best_player = db.Column(db.String(100), nullable=False)
    second_best_player = db.Column(db.String(100), nullable=False)
    third_best_player = db.Column(db.String(100), nullable=False)

    best_young_player = db.Column(db.String(100), nullable=False)
    best_goalkeeper = db.Column(db.String(100), nullable=False)

    top_scorer = db.Column(db.String(100), nullable=False)
    top_assister = db.Column(db.String(100), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="statistics_prediction")


class RealGroupMatchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    match_id = db.Column(
        db.Integer,
        db.ForeignKey('group_match.id'),
        unique=True,
        nullable=False
    )

    goals_team1 = db.Column(db.Integer, nullable=False)
    goals_team2 = db.Column(db.Integer, nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    match = db.relationship('GroupMatch')


class RealKnockoutResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    team_id = db.Column(
        db.Integer,
        db.ForeignKey('team.id'),
        unique=True,
        nullable=False
    )

    # GROUP, R32, R16, QF, SF, FINAL, WINNER
    eliminated_round = db.Column(db.String(10), nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship('Team')


class AdminConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    admin_password_hash = db.Column(db.String(256), nullable=True)
    initialized = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RealStatisticsResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    best_player = db.Column(db.String(100), nullable=False)
    second_best_player = db.Column(db.String(100), nullable=False)
    third_best_player = db.Column(db.String(100), nullable=False)

    best_young_player = db.Column(db.String(100), nullable=False)
    best_goalkeeper = db.Column(db.String(100), nullable=False)

    top_scorer = db.Column(db.String(100), nullable=False)
    top_assister = db.Column(db.String(100), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)