import datetime
import functools
import traceback

import discord
from discord.ext import commands, tasks

from typing import Never
import classes

from Functions import functions
import random
import Scoring
from Checks import checks

game_statuses = ["PICKING", "PLAYING", "SUBMITTED", "SCORED", "VOIDED"]


@functions.no_error_async
async def queue_game(queue: classes.Queue, players_ids: list[int], guild: discord.Guild, bot: commands.Bot):
    db, cursor = functions.database(guild.id)

    game_id = cursor.execute("SELECT game_count FROM game_count").fetchone()[0]

    cursor.execute("UPDATE game_count SET game_count=?", (game_id + 1,))
    db.commit()

    players = [await functions.fetch_member(player_id, guild) for player_id in players_ids]
    players_dict = {t.id: t for t in players}

    team1 = []
    team2 = []
    remaining_players = players

    for player in players:
        playerobj = classes.NewPlayer.from_player_id(player.id, guild)
        playerobj.games_ids += [game_id]

        player_cls = classes.NewPlayer.from_player_id(player.id, guild)
        player_cls.games_played += 1

    for player in players:
        party = checks.check_if_in_party(player.id, guild)
        if party is not None and party.leader_id == player.id:
            party.lastqueued = datetime.datetime.now().timestamp().__int__()
            await party.update_leader_games_count(bot)

            if len(team1) < len(team2):
                team1.extend([players_dict[t] for t in [party.leader_id] + party.members_ids])
            elif len(team2) < len(team1):
                team2.extend([players_dict[t] for t in [party.leader_id] + party.members_ids])
            else:
                if random.randint(1,2) == 1:
                    team1.extend([players_dict[t] for t in [party.leader_id] + party.members_ids])
                else:
                    team2.extend([players_dict[t] for t in [party.leader_id] + party.members_ids])

            remaining_players = [t for t in remaining_players if t not in team1 and t not in team2]

    if queue.automatic:
        if len(team1) == queue.player_count / 2:
            team2.extend(remaining_players)
            remaining_players.clear()
        elif len(team2) == queue.player_count / 2:
            team1.extend(remaining_players)
            remaining_players.clear()
        else:
            random_players_selected_for_team1 = random.sample(remaining_players, k=int(queue.player_count / 2))
            team1.extend(random_players_selected_for_team1)
            remaining_players = [remaining_player for remaining_player in list(remaining_players) if
                                 remaining_player not in team1]
            team2.extend(remaining_players)
            remaining_players.clear()

        game_tuple = (
            game_id,
            functions.list_to_str([str(team1_player.id) for team1_player in team1], ","),
            functions.list_to_str([str(team2_player.id) for team2_player in team2], ","),
            "",  # Remaining players ids
            queue.vc_id,
            None,
            None,  # Game vc ID
            None,
            None,
            queue.automatic,
            queue.ranked,
            "PLAYING"
        )

        cursor.execute("INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       game_tuple)
        db.commit()

        game = classes.Game.from_tuple(game_tuple, guild, bot)

        game.players = players
        game.team1 = team1
        game.team2 = team2
        game.remaining_players = remaining_players

        await game.create_game_tc()

        await game.fetch_webhook()

        await start_game(game)

        if not game.ranked:
            await game.void_game(bot.user, "Casual game", duration=45*60)
    else:
        start_game_bool = None
        team_pick_turn = None
        if len(team1) == queue.player_count / 2:
            team2.extend(remaining_players)
            remaining_players.clear()

            start_game_bool = True
        elif len(team2) == queue.player_count / 2:
            team1.extend(remaining_players)
            remaining_players.clear()

            start_game_bool = True

        # Picking captains
        if len(team1) == 0:
            team1.append(random.choice(remaining_players))
            remaining_players.remove(team1[0])
        if len(team2) == 0:
            team2.append(random.choice(remaining_players))
            remaining_players.remove(team2[0])

        if len(team1) == len(team2):
            team_pick_turn = 1
        else:
            team_pick_turn = 1 if len(team1) < len(team2) else 2

        cursor.execute("INSERT INTO picking VALUES (?, ?)",
                       (game_id, team_pick_turn))
        db.commit()

        if len(team1) == queue.player_count / 2:
            team2.extend(remaining_players)
            remaining_players.clear()

            start_game_bool = True
        elif len(team2) == queue.player_count / 2:
            team1.extend(remaining_players)
            remaining_players.clear()

            start_game_bool = True

        game_tuple = (
            game_id,
            ','.join([str(team1_player.id) for team1_player in team1]),
            ','.join([str(team2_player.id) for team2_player in team2]),
            ",".join([str(t.id) for t in remaining_players]),  # Remaining players ids
            queue.vc_id,
            None,
            None,  # Game vc ID
            None,
            None,
            queue.automatic,
            queue.ranked,
            "PLAYING" if start_game_bool else "PICKING"
        )

        cursor.execute("INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       game_tuple)
        db.commit()

        game = classes.Game.from_tuple(game_tuple, guild, bot)

        game.players = players
        game.team1 = list(team1)
        game.team2 = list(team2)
        game.remaining_players = list(remaining_players)

        await game.create_game_tc()

        await game.fetch_webhook()

        if start_game_bool:

            await start_game(game)

            if not game.ranked:
                await game.void_game(bot.user, "Casual game", duration=45 * 60)

        else:

            await game.webhook.send(embed=game.game_embed())

            await game.webhook.send(embed=functions.embed(
                guild,
                "",
                f"{f'{team1[0].mention}, you have `{len(team2) - len(team1) + 1}` picks left.' if team_pick_turn == 1 else f'{team2[0].mention}, you have `{len(team1) - len(team2) + 1}` picks left.'}"
            ))

            await game.create_game_vc_and_move()


async def start_game(game: classes.Game):
    game.status = "PLAYING"

    game.update_db()

    await game.send_game_started_embed()

    await game.create_team_vcs_and_move()

    await game.delete_game_vc()


async def start_game_if_possible(queue: classes.Queue, bot: commands.Bot):
    queue_players_ids = set(queue.queue_players_ids())

    player_count = 0
    parties = []
    non_party_players = []

    team1_left_space = queue.player_count/2
    team2_left_space = team1_left_space

    selected_for_queueing = []

    for player_id in queue_players_ids:
        selected_for_queueing = []

        party = checks.check_if_in_party(player_id, queue.guild)

        if party is None:
            non_party_players.append(player_id)
            player_count += 1
        elif party not in parties:
            if set(party.all_members).issubset(queue_players_ids):
                parties.append(party)
                player_count += len(party)

        if player_count >= queue.player_count:
            parties.sort(key=lambda p: len(p), reverse=True)
            for party in parties:

                if queue.player_count >= len(selected_for_queueing)+len(party):

                    if team1_left_space-len(party) >= 0 or team2_left_space-len(party) >= 0:

                        if team1_left_space >= team2_left_space:
                            team1_left_space -= len(party)
                        else:
                            team2_left_space -= len(party)

                        selected_for_queueing.extend(party.all_members)
                    else:
                        continue
                else:
                    break

            for non_party_player_id in non_party_players[:(queue.player_count - len(selected_for_queueing))]:
                selected_for_queueing.append(non_party_player_id)

            if len(selected_for_queueing) == queue.player_count:
                break

    if len(selected_for_queueing) == queue.player_count:
        queue.remove_queue_player(selected_for_queueing)
        await queue_game(queue, list(selected_for_queueing), queue.guild, bot)
