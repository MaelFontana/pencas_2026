from itertools import combinations
from .models import Group, Team, GroupMatch
from . import db

GROUP_DATA = {
    "A": ["🇲🇽 México", "🇿🇦 Sudáfrica", "🇰🇷 Corea del Sur", "🇨🇿 Chequia"],
    "B": ["🇨🇦 Canadá", "🇧🇦 Bosnia y Herzegovina", "🇶🇦 Catar", "🇨🇭 Suiza"],
    "C": ["🇧🇷 Brasil", "🇲🇦 Marruecos", "🇭🇹 Haití", "🏴 Escocia"],
    "D": ["🇺🇸 Estados Unidos", "🇵🇾 Paraguay", "🇦🇺 Australia", "🇹🇷 Turquía"],
    "E": ["🇩🇪 Alemania", "🇨🇼 Curazao", "🇨🇮 Costa de Marfil", "🇪🇨 Ecuador"],
    "F": ["🇳🇱 Países Bajos", "🇯🇵 Japón", "🇸🇪 Suecia", "🇹🇳 Túnez"],
    "G": ["🇧🇪 Bélgica", "🇪🇬 Egipto", "🇮🇷 Irán", "🇳🇿 Nueva Zelanda"],
    "H": ["🇪🇸 España", "🇨🇻 Cabo Verde", "🇸🇦 Arabia Saudita", "🇺🇾 Uruguay"],
    "I": ["🇫🇷 Francia", "🇸🇳 Senegal", "🇮🇶 Irak", "🇳🇴 Noruega"],
    "J": ["🇦🇷 Argentina", "🇩🇿 Argelia", "🇦🇹 Austria", "🇯🇴 Jordania"],
    "K": ["🇵🇹 Portugal", "🇨🇩 RD Congo", "🇺🇿 Uzbekistán", "🇨🇴 Colombia"],
    "L": ["🏴 Inglaterra", "🇭🇷 Croacia", "🇬🇭 Ghana", "🇵🇦 Panamá"]
}

def populate_groups_if_needed():
    if Group.query.first():
        return  # already populated

    for group_name, teams in GROUP_DATA.items():
        group = Group(name=group_name)
        db.session.add(group)
        db.session.flush()

        team_objs = []
        for name in teams:
            team = Team(name=name, group_id=group.id)
            db.session.add(team)
            team_objs.append(team)

        db.session.flush()

        for t1, t2 in combinations(team_objs, 2):
            db.session.add(
                GroupMatch(
                    group_id=group.id,
                    team1_id=t1.id,
                    team2_id=t2.id
                )
            )

    db.session.commit()
