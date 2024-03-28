import asyncio
import copy
import datetime
import io
import random
import sqlite3
from typing import Self, Optional, Iterable, Union

import chat_exporter
import discord
from discord.ext import commands

import errors
from Functions import functions

import Scoring


class Queue:
    def __init__(self, vc_id: int,
                 player_count: int,
                 automatic: int,
                 ranked: int,
                 min_elo: int,
                 max_elo: int,
                 extras: dict, /,
                 guild: discord.Guild):

        self.vc_id: int = vc_id
        self.player_count: int = player_count
        self.automatic: int = automatic
        self.ranked: int = ranked
        self.min_elo: int = min_elo
        self.max_elo: int = max_elo
        self.extras: dict = extras
        self.guild = guild

        self.vc = None

        self.db, self.cursor = functions.database(self.guild.id)

    @classmethod
    def from_tuple(cls, __tuple: tuple, guild: discord.Guild) -> Self:
        self = cls(__tuple[0],
                   __tuple[1],
                   __tuple[2],
                   __tuple[3],
                   __tuple[4],
                   __tuple[5],
                   __tuple[6],
                   guild
                   )
        return self

    def add_queue_player(self, players_ids: Union[Iterable[int], int]) -> None:

        if isinstance(players_ids, int):
            players_ids = (players_ids,)

        for player_id in players_ids:
            queue_players_ids_str_tuple = self.cursor.execute(
                "SELECT players_ids FROM queues_players WHERE queue_vc_id=?",
                (self.vc_id,)
            ).fetchone()

            if queue_players_ids_str_tuple is None:
                self.cursor.execute("INSERT INTO queues_players VALUES (?, ?)",
                                    (self.vc_id, ''))
                self.db.commit()

                queue_players_ids_str_tuple = ("",)

            queue_players_ids_str = queue_players_ids_str_tuple[0]

            if str(player_id) not in queue_players_ids_str:

                if queue_players_ids_str != "":

                    queue_players_ids_str += f",{player_id}"

                else:

                    queue_players_ids_str += f"{player_id}"

                self.cursor.execute("UPDATE queues_players SET players_ids=? WHERE queue_vc_id=?",
                                    (queue_players_ids_str, self.vc_id))
                self.db.commit()

        return None

    def remove_queue_player(self, players_ids: Union[Iterable[int], int]) -> None:

        if isinstance(players_ids, int):
            players_ids = (players_ids,)

        for player_id in players_ids:
            queue_players_ids_str_tuple = self.cursor.execute(
                "SELECT players_ids FROM queues_players WHERE queue_vc_id=?",
                (self.vc_id,)
            ).fetchone()

            if queue_players_ids_str_tuple is None:
                self.cursor.execute("INSERT INTO queues_players VALUES (?, ?)",
                                    (self.vc_id, ''))
                self.db.commit()
                queue_players_ids_str_tuple = ("",)

            queue_players_ids_str = queue_players_ids_str_tuple[0]

            if str(player_id) in queue_players_ids_str:
                queue_players_ids_str = queue_players_ids_str.replace(f",{player_id}", "")
                queue_players_ids_str = queue_players_ids_str.replace(f"{player_id},", "")
                queue_players_ids_str = queue_players_ids_str.replace(f"{player_id}", "")

                self.cursor.execute("UPDATE queues_players SET players_ids=? WHERE queue_vc_id=?",
                                    (queue_players_ids_str, self.vc_id))
                self.db.commit()

        return None

    def queue_players_ids(self) -> list[int]:

        queue_players_ids_not_split: str = self.cursor.execute(
            "SELECT players_ids FROM queues_players WHERE queue_vc_id=?",
            (self.vc_id,)
        ).fetchone()[0]

        if queue_players_ids_not_split == "":
            queue_players_ids = []
        else:

            queue_players_ids = [int(queue_player_id) for queue_player_id in queue_players_ids_not_split.split(",") if
                                 queue_player_id != ""]

        return queue_players_ids

    async def vc(self) -> discord.VoiceChannel:
        self.vc: discord.VoiceChannel = await functions.fetch_channel(self.vc_id, self.guild)

        return self.vc


class NewPlayer:
    def __init__(
            self,
            player_id: int,
            ign: str,
            elo: int,
            peak_elo: int,
            wins: int,
            winstreak: int,
            peak_winstreak: int,
            losses: int,
            losestreak: int,
            peak_losestreak: int,
            mvps: int,
            games_played: int,
            games_ids: list[int],
            guild: discord.Guild
    ):
        self._weekly = None
        self._daily = None
        self.player_id = player_id
        self.ign = ign
        self._elo: int = elo
        self.peak_elo: int = peak_elo
        self._wins: int = wins
        self._winstreak: int = winstreak
        self._peak_winstreak: int = peak_winstreak
        self._losses: int = losses
        self._losestreak: int = losestreak
        self._peak_losestreak: int = peak_losestreak
        self._mvps: int = mvps
        self._games_played: int = games_played
        self._games_ids: list[int] = games_ids
        self.guild: discord.Guild = guild

        self._db, self._cursor = functions.database(self.guild.id)

        self._rank = None

    @property
    def elo(self):
        return self._elo

    @elo.setter
    def elo(self, new_elo: int):
        old_elo = self._elo
        self._elo = new_elo if new_elo > 0 else 0

        if self._elo > self.peak_elo:
            self.peak_elo = self._elo

        self._cursor.execute("UPDATE players SET elo=?,peak_elo=? WHERE id=?",
                             (self._elo, self.peak_elo, self.player_id))
        self._db.commit()
        WeeklyDaily.elo(self.player_id, self._elo - old_elo, self._db)

    @property
    def wins(self):
        return self._wins

    @wins.setter
    def wins(self, new_wins: int):
        old_wins = self._wins
        self._wins = new_wins

        self._cursor.execute("UPDATE players SET wins=? WHERE id=?",
                             (self._wins, self.player_id))
        self._db.commit()
        WeeklyDaily.wins(self.player_id, self._wins - old_wins, self._db)

    @property
    def losses(self):
        return self._losses

    @losses.setter
    def losses(self, new_losses: int):
        old_losses = self._losses
        self._losses = new_losses

        self._cursor.execute("UPDATE players SET losses=? WHERE id=?",
                             (self._losses, self.player_id))
        self._db.commit()
        WeeklyDaily.losses(self.player_id, self._losses - old_losses, self._db)

    @property
    def winstreak(self):
        return self._winstreak

    @winstreak.setter
    def winstreak(self, new_winstreak: int):
        self._winstreak = new_winstreak

        if self._winstreak > self.peak_winstreak:
            self.peak_winstreak = self._winstreak

        if self._losestreak > 0 and self._winstreak > 0:
            self._losestreak = 0

        self._cursor.execute("UPDATE players SET winstreak=?,losestreak=? WHERE id=?",
                             (self._winstreak, self._losestreak, self.player_id))
        self._db.commit()

    @property
    def peak_winstreak(self):
        return self._peak_winstreak

    @peak_winstreak.setter
    def peak_winstreak(self, new_peak_winstreak: int):
        self._peak_winstreak = new_peak_winstreak

        db, cursor = functions.database(self.guild.id)

        cursor.execute("UPDATE players SET peak_winstreak=? WHERE id=?",
                       (self._peak_winstreak, self.player_id))
        db.commit()

    @property
    def losestreak(self):
        return self._losestreak

    @losestreak.setter
    def losestreak(self, new_losestreak: int):
        self._losestreak = new_losestreak

        if self._losestreak > self.peak_losestreak:
            self.peak_losestreak = self._losestreak

        if self._winstreak > 0 and self._losestreak > 0:
            self._winstreak = 0

        self._cursor.execute("UPDATE players SET winstreak=?,losestreak=? WHERE id=?",
                             (self._winstreak, self._losestreak, self.player_id))
        self._db.commit()

    @property
    def peak_losestreak(self):
        return self._peak_losestreak

    @peak_losestreak.setter
    def peak_losestreak(self, new_peak_losestreak: int):
        self._peak_losestreak = new_peak_losestreak

        db, cursor = functions.database(self.guild.id)

        cursor.execute("UPDATE players SET peak_losestreak=? WHERE id=?",
                       (self._peak_losestreak, self.player_id))
        db.commit()

    @property
    def mvps(self):
        return self._mvps

    @mvps.setter
    def mvps(self, new_mvps: int):
        old_mvps = self._mvps
        self._mvps = new_mvps

        self._cursor.execute("UPDATE players SET mvps=? WHERE id=?",
                             (self._mvps, self.player_id))
        self._db.commit()
        WeeklyDaily.mvps(self.player_id, self._mvps - old_mvps, self._db)

    @property
    def games_played(self):
        return self._games_played

    @games_played.setter
    def games_played(self, new_games_played: int):
        old_games_played = self._games_played
        self._games_played = new_games_played

        self._cursor.execute("UPDATE players SET games_played=? WHERE id=?",
                             (self._games_played, self.player_id))
        self._db.commit()
        WeeklyDaily.games_played(self.player_id, self._games_played - old_games_played, self._db)

    @property
    def games_ids(self):
        return self._games_ids

    @games_ids.setter
    def games_ids(self, new_games_ids: list[int]):
        self._cursor.execute("UPDATE players SET games_ids=? WHERE id=?",
                             (",".join([str(t) for t in new_games_ids]), self.player_id))
        self._db.commit()

    @property
    def rank(self):
        for rank_tuple in self._cursor.execute("SELECT * FROM ranks").fetchall():
            rank_instance = Rank.from_tuple(rank_tuple, self.guild)
            if rank_instance.starting_elo <= self.elo <= rank_instance.ending_elo:
                self._rank = rank_instance
                break
        return self._rank

    @property
    def streak(self):
        return self.winstreak if self.winstreak > 0 else -self.losestreak

    @property
    def wlr(self):
        return self.wins / (self.losses if self.losses != 0 else 1)

    @property
    def winrate(self):
        return (self.wins / (self.games_played if self.games_played != 0 else 1)) * 100

    @property
    def leaderboard_spot(self):
        players = self._cursor.execute("SELECT elo,id FROM players").fetchall()
        players.sort(reverse=True)
        return players.index((self.elo, self.player_id)) + 1

    @property
    def weekly_elo(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT elo FROM weekly WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def weekly_wins(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT wins FROM weekly WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def weekly_losses(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT losses FROM weekly WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def weekly_mvps(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT mvps FROM weekly WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def weekly_games_played(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT games_played FROM weekly WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def weekly_wlr(self):
        return round(self.weekly_wins / (self.weekly_losses or 1), 1)

    @property
    def weekly_winrate(self):
        return round(self.weekly_wins / (self.games_played or 1), 2)

    @property
    def daily_elo(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT elo FROM daily WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def daily_wins(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT wins FROM daily WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def daily_losses(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT losses FROM daily WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def daily_mvps(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT mvps FROM daily WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def daily_games_played(self):
        db, cursor = functions.database(self.guild.id)
        WeeklyDaily.create_daily_weekly_stats(self.player_id, db)
        return cursor.execute("SELECT games_played FROM daily WHERE id=?",
                              (self.player_id,)).fetchone()[0]

    @property
    def daily_wlr(self):
        return round(self.daily_wins / (self.daily_losses or 1), 1)

    @property
    def daily_winrate(self):
        return round(self.daily_wins / (self.games_played or 1), 2)

    def fix_streak(self):
        winstreak = 0
        losestreak = 0
        for game_id in self.games_ids[::-1]:
            game = Game.from_game_id(game_id, self.guild)
            if game.status == "SCORED":
                scored_game = ScoredGame.from_game_id(game_id, self.guild)
                if self.player_id in scored_game.winner_team_ids:
                    if losestreak > 0:
                        break
                    winstreak += 1
                else:
                    if winstreak > 0:
                        break
                    losestreak += 1

        self.winstreak = winstreak
        self.losestreak = losestreak

    @classmethod
    def from_tuple(cls, __tuple: tuple, guild: discord.Guild):

        return cls(
            __tuple[0],
            __tuple[1],
            __tuple[2],
            __tuple[3],
            __tuple[4],
            __tuple[5],
            __tuple[6],
            __tuple[7],
            __tuple[8],
            __tuple[9],
            __tuple[10],
            __tuple[11],
            [] if __tuple[12] == '' or __tuple is None else
            [int(t) for t in __tuple[12].split(",")],
            guild
        )

    @classmethod
    def from_player_id(cls, __player_id: int, guild: discord.Guild):
        db, cursor = functions.database(guild.id)

        player_tuple = cursor.execute("SELECT * FROM players WHERE id=?",
                                      (__player_id,)).fetchone()

        if player_tuple is None:
            return None

        else:
            return cls.from_tuple(player_tuple, guild)

    def reset_stats(self):
        db, cursor = functions.database(self.guild.id)
        cursor.execute("UPDATE players SET elo=0, "
                       "peak_elo=0, "
                       "wins=0, "
                       "winstreak=0, "
                       "peak_winstreak=0, "
                       "losses=0, "
                       "losestreak=0, "
                       "peak_losestreak=0, "
                       "mvps=0, "
                       "games_played=0, "
                       "games_ids='' WHERE id=?",
                       (self.player_id,))
        db.commit()
        del self

    def calculate_game_outcome(self, win: bool, mvp: bool):
        old_self = copy.copy(self)
        if win:
            self.elo += self.rank.win_elo
            self.wins += 1
            self.winstreak += 1
        else:
            self.elo += self.rank.lose_elo
            self.losses += 1
            self.losestreak += 1

        if mvp:
            self.elo += self.rank.mvp_elo
            self.mvps += 1

        return old_self, self


class Game:
    def __init__(self, game_id: int,
                 team1_players_ids: list[int],
                 team2_players_ids: list[int],
                 remaining_players_ids: list[int],
                 queue_vc_id: int,
                 game_tc_id: int,
                 game_vc_id: int,
                 team1_vc_id: int,
                 team2_vc_id: int,
                 automatic: int,
                 ranked: int,
                 status: str,
                 guild: discord.Guild,
                 bot: commands.Bot
                 ):
        self._scored_game = None
        self.game_vc = None
        self.team1_vc: Optional[discord.VoiceChannel] = None
        self.team2_vc: Optional[discord.VoiceChannel] = None
        self.game_id: int = game_id
        self.team1_players_ids: list[int] = team1_players_ids
        self.team2_players_ids: list[int] = team2_players_ids
        self.remaining_players_ids: list[int] = remaining_players_ids
        self.queue_vc_id: int = queue_vc_id
        self.game_tc_id: int = game_tc_id
        self.game_vc_id: int = game_vc_id
        self.team1_vc_id: int = team1_vc_id
        self.team2_vc_id: int = team2_vc_id
        self.automatic: int = automatic
        self.ranked: int = ranked
        self.status: str = status
        self.guild: discord.Guild = guild
        self.bot = bot

        self.webhook: Union[discord.Webhook, None] = None
        self.game_tc: Union[discord.TextChannel, None] = None

        self.players: list[discord.Member] = []
        self.team1: list[discord.Member] = []
        self.team2: list[discord.Member] = []
        self.remaining_players: list[discord.Member] = []

        self._all_players = []

        self._queue = None

    @property
    def queue(self):
        if self._queue is not None:
            return self._queue

        db, cursor = functions.database(self.guild.id)

        queue_tuple = cursor.execute("SELECT * FROM queues WHERE queue_vc_id=?",
                                     (self.queue_vc_id,)).fetchone()

        return Queue.from_tuple(queue_tuple, self.guild)

    @property
    def all_players(self) -> list[NewPlayer]:
        if self._all_players == []:
            for player_id in self.players_ids:
                self._all_players.append(NewPlayer.from_player_id(player_id, self.guild))

        return self._all_players

    @classmethod
    def from_tuple(cls, __tuple: tuple, guild: discord.Guild, bot: commands.Bot) -> Self:
        team1_players_ids = [int(team1_player_id) for team1_player_id in __tuple[1].split(",")] \
            if __tuple[1] != "" else []
        team2_players_ids = [int(team2_player_id) for team2_player_id in __tuple[2].split(",")] \
            if __tuple[2] != "" else []
        remaining_players_ids = [int(remaining_player) for remaining_player in __tuple[3].split(",")] \
            if __tuple[3] != "" else []
        return cls(
            __tuple[0],
            team1_players_ids,
            team2_players_ids,
            remaining_players_ids,
            __tuple[4],
            __tuple[5],
            __tuple[6],
            __tuple[7],
            __tuple[8],
            __tuple[9],
            __tuple[10],
            __tuple[11],
            guild,
            bot
        )

    @property
    def players_ids(self):
        return self.team1_players_ids + self.team2_players_ids + self.remaining_players_ids

    @classmethod
    def from_game_tc(cls, game_tc: discord.TextChannel, bot: commands.Bot) -> Union[Self, None]:
        db, cursor = functions.database(game_tc.guild.id)

        game_tuple = cursor.execute("SELECT * FROM games WHERE game_tc_id=?",
                                    (game_tc.id,)).fetchone()

        if game_tuple is None:
            return None
        else:
            game = cls.from_tuple(game_tuple, game_tc.guild, bot)
            game.tc = game_tc
            return game

    @classmethod
    def from_game_id(cls, game_id: int, guild: discord.Guild, bot: Optional[commands.Bot] = None) -> Union[Self, None]:
        db, cursor = functions.database(guild.id)

        game_tuple = cursor.execute("SELECT * FROM games WHERE game_id=?",
                                    (game_id,)).fetchone()
        if game_tuple is None:
            return None

        else:
            return cls.from_tuple(game_tuple, guild, bot)

    def pick_turn(self):
        db, cursor = functions.database(self.guild.id)

        team_turn_int_tuple = cursor.execute("SELECT team_turn FROM picking WHERE game_id=?",
                                             (self.game_id,)).fetchone()

        if team_turn_int_tuple is None:
            return None
        else:
            return team_turn_int_tuple[0]

    def update_pick_turn(self):
        db, cursor = functions.database(self.guild.id)

        previous_pick_turn = self.pick_turn()

        if previous_pick_turn == 1 and len(self.team1_players_ids) > len(self.team2_players_ids):
            cursor.execute("UPDATE picking SET team_turn=2 WHERE game_id=?",
                           (self.game_id,))
            db.commit()
        elif previous_pick_turn == 2 and len(self.team2_players_ids) > len(self.team1_players_ids):
            cursor.execute("UPDATE picking SET team_turn=1 WHERE game_id=?",
                           (self.game_id,))
            db.commit()
        else:
            pass

    def fetch(self):
        db, cursor = functions.database(self.guild.id)
        game_tuple = cursor.execute("SELECT * FROM games WHERE game_id=?",
                                    (self.game_id,)).fetchone()
        new_self = self.from_tuple(game_tuple, self.guild, self.bot)

        for arg in new_self.__dict__:
            setattr(self, arg, getattr(new_self, arg, None))

    def can_be_submitted(self) -> bool:
        self.fetch()
        if self.status == "PLAYING":
            return True
        else:
            return False

    def can_be_scored(self) -> bool:
        self.fetch()
        if self.status == "SUBMITTED":
            return True
        else:
            return False

    async def delete_game_vc(self):
        if self.game_vc_id is None or self.game_vc_id == "":
            return None
        else:
            self.game_vc = self.game_vc or await functions.fetch_channel(self.game_vc_id, self.guild)

            await self.game_vc.delete(reason="Picking ended. Game started.")
            return None

    async def fetch_tc(self) -> discord.TextChannel:
        if self.game_tc is None:
            try:
                self.game_tc = await functions.fetch_channel(self.game_tc_id, self.guild)
            except:
                self.game_tc = None
            return self.game_tc
        else:
            return self.game_tc

    async def fetch_webhook(self) -> discord.Webhook:
        if self.webhook is None:
            await self.fetch_tc()
            self.webhook = await functions.fetch_webhook(self.game_tc, self.bot, webhook_name=f"Game#{self.game_id}")
            return self.webhook
        else:
            return self.webhook

    def update_db(self) -> None:
        try:
            self.game_tc_id = self.game_tc.id
        except AttributeError:
            pass

        try:
            self.team1_vc_id = self.team1_vc.id
        except AttributeError:
            pass

        try:
            self.team2_vc_id = self.team2_vc.id
        except AttributeError:
            pass

        db, cursor = functions.database(self.guild.id)

        cursor.execute("UPDATE games SET team1_players_ids=?, "
                       "team2_players_ids=?, "
                       "remaining_players_ids=?, "
                       "queue_vc_id=?, "
                       "game_tc_id=?, "
                       "game_vc_id=?, "
                       "team1_vc_id=?, "
                       "team2_vc_id=?, "
                       "automatic=?, "
                       "ranked=?, "
                       "status=? WHERE game_id=?",
                       (
                           functions.list_to_str(self.team1_players_ids, ","),
                           functions.list_to_str(self.team2_players_ids, ","),
                           functions.list_to_str(self.remaining_players_ids, ","),
                           self.queue_vc_id,
                           self.game_tc_id,
                           self.game_vc_id,
                           self.team1_vc_id,
                           self.team2_vc_id,
                           self.automatic,
                           self.ranked,
                           self.status,
                           self.game_id
                       )
                       )
        db.commit()

    async def fetch_players(self) -> list[discord.Member]:
        for team1_player_id in self.team1_players_ids:
            team1_player = await functions.fetch_member(team1_player_id, self.guild)
            if team1_player not in self.team1:
                self.team1.append(team1_player)
            if team1_player not in self.players:
                self.players.append(team1_player)
        for team2_player_id in self.team2_players_ids:
            team2_player = await functions.fetch_member(team2_player_id, self.guild)
            if team2_player not in self.team2:
                self.team2.append(team2_player)
            if team2_player not in self.players:
                self.players.append(team2_player)
        for remaining_player_id in self.remaining_players_ids:
            remaining_player = await functions.fetch_member(remaining_player_id, self.guild)
            if remaining_player not in self.remaining_players:
                self.remaining_players.append(remaining_player)
            if remaining_player not in self.players:
                self.players.append(remaining_player)

        return self.players

    async def create_game_tc(self) -> discord.TextChannel:
        await self.fetch_players()

        channel_name_prefix = functions.get_info_value("CHANNELNAMEPREFIX", self.guild)
        game_channels_category = await functions.fetch_channel("GAMECHANNELSCATEGORY", self.guild)

        game_tc_overwrites = game_channels_category.overwrites

        for player in self.players:
            game_tc_overwrites.update({player: discord.PermissionOverwrite(view_channel=True, send_messages=True)})

        self.game_tc = await self.guild.create_text_channel(
            name=f"{channel_name_prefix}game#{self.game_id}",
            category=game_channels_category,
            overwrites=game_tc_overwrites
        )

        self.update_db()

        return self.game_tc

    async def create_team_vcs_and_move(self) -> tuple[discord.VoiceChannel, discord.VoiceChannel]:

        await self.fetch_players()

        channel_name_prefix = functions.get_info_value("CHANNELNAMEPREFIX", self.guild)
        default_vc_region = functions.get_info_value("DEFAULTVCREGION", self.guild)
        team_vcs_category = await functions.fetch_channel("TEAMVCSCATEGORY", self.guild)

        team1_overwrites = team_vcs_category.overwrites

        for team1_player in self.team1:
            team1_overwrites.update({team1_player: discord.PermissionOverwrite(connect=True)})

        team2_overwrites = team_vcs_category.overwrites

        for team2_player in self.team2:
            team2_overwrites.update({team2_player: discord.PermissionOverwrite(connect=True)})

        self.team1_vc = await self.guild.create_voice_channel(name=f"{channel_name_prefix}Game#{self.game_id} | Team 1",
                                                              category=team_vcs_category,
                                                              rtc_region=default_vc_region,
                                                              overwrites=team1_overwrites)

        self.team2_vc = await self.guild.create_voice_channel(name=f"{channel_name_prefix}Game#{self.game_id} | Team 2",
                                                              category=team_vcs_category,
                                                              rtc_region=default_vc_region,
                                                              overwrites=team2_overwrites)

        for team1_player in self.team1:
            try:
                await team1_player.edit(voice_channel=self.team1_vc)
            except discord.HTTPException as e:
                pass

        for team2_player in self.team2:
            try:
                await team2_player.edit(voice_channel=self.team2_vc)
            except discord.HTTPException as e:
                pass

        self.update_db()

        return self.team1_vc, self.team2_vc

    async def send_game_started_embed(self) -> None:
        await self.fetch_webhook()

        game_started_embed_title: str = functions.get_info_value("GAMESTARTEDEMBEDTITLE", self.guild)
        game_started_embed_description: str = functions.get_info_value("GAMESTARTEDEMBEDDESCRIPTION", self.guild)

        game_started_embed_fields = [
            ["**Team 1**", "\n".join([f'<@{team1_player_id}>' for team1_player_id in self.team1_players_ids]), True],
            ["**Team 2**", "\n".join([f'<@{team2_player_id}>' for team2_player_id in self.team2_players_ids]), True]
        ]

        if self.remaining_players_ids != []:
            game_started_embed_fields.append(
                ["**Remaining Players**",
                 "\n".join([f'<@{remaining_player_id}>' for remaining_player_id in self.remaining_players_ids]),
                 True]
            )

        db, cursor = functions.database(self.guild.id)

        if all_maps := cursor.execute('SELECT * FROM maps').fetchall():
            game_started_embed_fields.append([
                "Map",
                str(random.choice(all_maps)[0]),
                False
            ])

        embeds = [
            functions.embed(
                self.guild,
                embed_title=game_started_embed_title.format(game_id=self.game_id),
                embed_description=game_started_embed_description.format(game_id=self.game_id),
                embed_fields=game_started_embed_fields,
                embed_footer_text=True,
                embed_footer_icon_url=True
            ),
            functions.embed(
                self.guild,
                embed_title="Rules",
                embed_description=functions.get_info_value("RULES", self.guild),
                embed_footer_text=True,
                embed_footer_icon_url=True
            )
        ]

        game_started_message = await self.webhook.send(
            content=''.join([f'<@{t}>' for t in self.players_ids]),
            embeds=embeds,
            wait=True
        )

        await game_started_message.pin()

        return None

    async def sequence_cleaner(self):
        await self.fetch_webhook()

        msg = await self.webhook.send(
            embed=functions.embed(
                self.guild,
                "Thanks for playing",
                ":arrows_counterclockwise: Archiving channel...",
                embed_footer_text="Ranked Bedwars by imfabulousxd",
                embed_color="ALTERNATIVE"
            ),
            wait=True
        )

        game_channels_category = await functions.fetch_channel("GAMECHANNELSCATEGORY", self.guild)

        new_overwrites = game_channels_category.overwrites

        await self.fetch_tc()

        await self.game_tc.edit(overwrites=new_overwrites)

        await self.send_scoring_message()

        await self.close_game_tc(f"Screenshot Submission")

        await self.close_game_and_team_vcs()

    def is_scored(self):
        if self.status == "SCORED":
            return True
        else:
            return False

    @property
    def scored_game(self):
        self._scored_game = self._scored_game or ScoredGame.from_game_id(self.game_id, self.guild, self.bot)
        return self._scored_game

    async def game_scoring_embed(self):
        scored = self.is_scored()

        db, cursor = functions.database(self.guild.id)
        game_ssurl_submitedbyid_tuple = cursor.execute(
            "SELECT screenshot_url, submitted_by FROM game_screenshots WHERE game_id=?",
            (self.game_id,)).fetchone()

        ss_url = game_ssurl_submitedbyid_tuple[0]
        submitted_by_id = game_ssurl_submitedbyid_tuple[1]
        submitted_by = await functions.fetch_member(submitted_by_id, self.guild)

        scoring_embed = functions.embed(
            self.guild,
            f"Game#{self.game_id}",
            embed_author_name=f"{self.guild.name}",
            embed_author_icon_url=self.guild.icon.url,
            embed_fields=[
                ["Team 1", "\n".join([f'<@{t}>' for t in self.team1_players_ids]), True],
                ["Team 2", "\n".join([f'<@{t}>' for t in self.team2_players_ids]), True],
                ["Scoring Info", f"**Scorer :** {f'<@{self.scored_game.scored_by}>' if scored else 'None'}\n"
                                 f"**Selected Winner :** `{self.scored_game.winner if scored else 'Not Selected Yet'}`\n"
                                 f"**MVPs :** {''.join([f'<@{t}>' for t in self.scored_game.mvps_ids]) if scored else 'None'}\n"
                                 f"**State :** `{self.status}`", False]
            ],
            embed_footer_text=f"Subbmitted by {submitted_by.name}",
            embed_timestamp=True
        )
        return scoring_embed

    async def send_scoring_message(self):
        scoring_reports_channel = await functions.fetch_channel("SCORINGREPORTS", self.guild)

        db, cursor = functions.database(self.guild.id)
        game_ssurl_submitedbyid_tuple = cursor.execute(
            "SELECT screenshot_url, submitted_by FROM game_screenshots WHERE game_id=?",
            (self.game_id,)).fetchone()
        ss_url = game_ssurl_submitedbyid_tuple[0]
        image_bytes, image_type = await functions.get_image_bytes_from_url(ss_url)
        image_file = discord.File(fp=io.BytesIO(image_bytes), filename=f"game-{self.game_id}.{image_type}")

        await scoring_reports_channel.send(
            embed=await self.game_scoring_embed(),
            view=Scoring.views.ScoreGameView(self),
            file=image_file
        )

        await scoring_reports_channel.send(
            content=functions.fetch_role('SCORER', self.guild).mention,
            delete_after=3
        )

    async def score_game(self, winner_team_number: int, mvps_players_ids: list[int],
                         scored_by: discord.Member):
        if not self.can_be_scored():
            raise errors.ScoringError(f"Game#{self.game_id} cannot be scored at its' current state.")

        team1 = []
        for team1_player_id in self.team1_players_ids:
            player = NewPlayer.from_player_id(team1_player_id, self.guild)
            old_team1_player, new_team1_player = player.calculate_game_outcome(
                True if winner_team_number == 1 else False,
                True if player.player_id in mvps_players_ids else False)
            team1.append((old_team1_player, new_team1_player))

        team2 = []
        for team2_player_id in self.team2_players_ids:
            player = NewPlayer.from_player_id(team2_player_id, self.guild)
            old_team2_player, new_team2_player = player.calculate_game_outcome(
                True if winner_team_number == 2 else False,
                True if player.player_id in mvps_players_ids else False)
            team2.append((old_team2_player, new_team2_player))

        scoring_channel = await functions.fetch_channel('SCORING', self.guild)

        team1_ids_elo_changes = ""
        for old_team1_player, new_team1_player in team1:
            team1_ids_elo_changes += f"{new_team1_player.player_id},{new_team1_player.elo - old_team1_player.elo},"
        team1_ids_elo_changes = team1_ids_elo_changes[:-1]

        team2_ids_elo_changes = ""
        for old_team2_player, new_team2_player in team2:
            team2_ids_elo_changes += f"{new_team2_player.player_id},{new_team2_player.elo - old_team2_player.elo},"
        team2_ids_elo_changes = team2_ids_elo_changes[:-1]

        db, cursor = functions.database(self.guild.id)

        cursor.execute("INSERT INTO scored_games VALUES (?, ?, ?, ?, ?, ?)",
                       (self.game_id,
                        winner_team_number,
                        team1_ids_elo_changes,
                        team2_ids_elo_changes,
                        ",".join([str(t) for t in mvps_players_ids]),
                        scored_by.id))
        db.commit()

        team1_player_descriptions = []
        for old_team1_player, new_team1_player in team1:
            win_or_lose_emoji = '🟩' if winner_team_number == 1 else '🟥'
            team1_player_descriptions.append(
                f"{'🔥' if new_team1_player.player_id in mvps_players_ids else win_or_lose_emoji}"
                f"<@{new_team1_player.player_id}> "
                f"`({'+' if new_team1_player.elo >= old_team1_player.elo else '-'})"
                f"{abs(new_team1_player.elo - old_team1_player.elo)}` "
                f"[`{old_team1_player.elo}` ➜ `{new_team1_player.elo}`]")

        team2_player_descriptions = []
        for old_team2_player, new_team2_player in team2:
            win_or_lose_emoji = '🟩' if winner_team_number == 2 else '🟥'
            team2_player_descriptions.append(
                f"{'🔥' if new_team2_player.player_id in mvps_players_ids else win_or_lose_emoji}"
                f"<@{new_team2_player.player_id}> "
                f"`({'+' if new_team2_player.elo >= old_team2_player.elo else '-'})"
                f"{abs(new_team2_player.elo - old_team2_player.elo)}` "
                f"[`{old_team2_player.elo}` ➜ `{new_team2_player.elo}`]")

        self.status = "SCORED"

        self.update_db()

        game_scored_embed_fields = [
            ["**Team 1**", "\n".join(team1_player_descriptions), False],
            ["**Team 2**", "\n".join(team2_player_descriptions), False]
        ]

        game_scored_embed = functions.embed(
            self.guild,
            "Scoring System",
            f"Game#{self.game_id}",
            embed_fields=game_scored_embed_fields,
            embed_footer_text=f"Scored by {scored_by.name}",
            embed_timestamp=True
        )

        webhook = await functions.fetch_webhook(scoring_channel, self.bot, webhook_name="Scoring")

        game_scored_msg = await webhook.send(
            content=f"Game#{self.game_id}",
            wait=True
        )

        await game_scored_msg.edit(
            content="\u200b".join([f'<@{p}>' for p in self.team1_players_ids + self.team2_players_ids]),
            embed=game_scored_embed
        )

        await self.fetch_players()

        for player in self.players:
            await functions.fix(player, registered_role_check=True,
                                nick_check=True,
                                rank_check=True,
                                streak_check=True)

        return game_scored_msg

    def game_embed(self):
        game_started_embed_fields = [
            ["**Team 1**", "\n".join([f'<@{team1_player_id}>' for team1_player_id in self.team1_players_ids]), True],
            ["**Team 2**", "\n".join([f'<@{team2_player_id}>' for team2_player_id in self.team2_players_ids]), True]
        ]

        if self.remaining_players_ids != []:
            game_started_embed_fields.append(
                ["**Remaining Players**",
                 "\n".join([f'<@{remaining_player_id}>' for remaining_player_id in self.remaining_players_ids]),
                 True]
            )

        game_embed = functions.embed(
            self.guild,
            embed_title=f"Game#{self.game_id}",
            embed_fields=game_started_embed_fields,
            embed_footer_text=True,
            embed_footer_icon_url=True
        )

        return game_embed

    async def fetch_team_vcs(self):
        if self.team1_vc is None:
            try:
                self.team1_vc = await functions.fetch_channel(self.team1_vc_id, self.guild)
            except:
                self.team1_vc = None

        if self.team2_vc is None:
            try:
                self.team2_vc = await functions.fetch_channel(self.team2_vc_id, self.guild)
            except:
                self.team2_vc = None

    async def fetch_game_vc(self):
        if self.game_vc_id is None or self.game_vc_id == "":
            self.game_vc = None
        else:
            try:
                self.game_vc = await functions.fetch_channel(
                    self.game_vc_id, self.guild
                )
            except:
                self.game_vc = None
        return

    async def close_game_and_team_vcs(self):
        await self.fetch_team_vcs()
        await self.fetch_game_vc()

        waiting_room = await functions.fetch_channel("WAITINGROOM", self.guild)

        if self.team1_vc is not None:
            for team1_vc_member in self.team1_vc.members:
                try:
                    await team1_vc_member.edit(
                        voice_channel=waiting_room
                    )
                except discord.HTTPException:
                    pass
            await self.team1_vc.delete()

        if self.team2_vc is not None:
            for team2_vc_member in self.team2_vc.members:
                try:
                    await team2_vc_member.edit(
                        voice_channel=waiting_room
                    )
                except discord.HTTPException:
                    pass
            await self.team2_vc.delete()

        if self.game_vc is not None:
            for game_vc_member in self.game_vc.members:
                try:
                    await game_vc_member.edit(
                        voice_channel=waiting_room
                    )
                except discord.HTTPException:
                    pass
            await self.game_vc.delete()

    async def close_game_tc(self, reason: str, duration: int = 30):
        await self.fetch_tc()

        if self.game_tc is None:
            return

        # noinspection PyTypeChecker
        closing_game_tc_task = asyncio.create_task(functions.close_channel(
            self.game_tc,
            self.bot,
            datetime.datetime.now() + datetime.timedelta(seconds=duration),
            self.bot.user,
            reason,
            await self.fetch_webhook()
        ))

        try:
            exported_chat = await chat_exporter.export(
                self.game_tc,
                tz_info="Iran",
                bot=self.bot
            )

            game_transcripts_channel = await functions.fetch_channel("GAMETRANSCRIPTS", self.guild)

            game_transcripts_channel_webhook = await functions.fetch_webhook(game_transcripts_channel, self.bot)

            await game_transcripts_channel_webhook.send(
                content=f"Game#{self.game_id}",
                file=discord.File(
                    io.BytesIO(exported_chat.encode()),
                    filename=f"game-{self.game_id}.ts.html"
                ),
                embed=functions.embed(
                    self.guild,
                    "Games Log",
                    "Chat for game#{}".format(self.game_id),
                    embed_fields=[["**Reason**", reason, False]]
                )
            )
        except:
            pass

        await closing_game_tc_task

    async def close_tc_and_vcs(self, reason: str = "Not Specified", duration: int = 30):
        await self.close_game_tc(reason, duration)
        await self.close_game_and_team_vcs()

    async def void_game(self, voided_by: discord.Member, reason: str, duration: int = 30):
        self.fetch()

        if self.status not in ['PICKING', 'PLAYING', 'SUBMITTED']:
            raise errors.QueueError("You cannot void this self in its' current state.")

        db, cursor = functions.database(self.guild.id)

        cursor.execute("INSERT INTO voided_games VALUES (?, ?)",
                       (self.game_id, voided_by.id))
        db.commit()

        cursor.execute("DELETE FROM scored_games WHERE game_id=?",
                       (self.game_id,))
        db.commit()

        self.status = "VOIDED"

        self.update_db()

        await self.close_tc_and_vcs(f"Game voided by {voided_by.mention} (`{reason}`)", duration=duration)

    async def create_game_vc_and_move(self):
        self.fetch()
        await self.fetch_players()

        game_vcs_category = await functions.fetch_channel('TEAMVCSCATEGORY', self.guild)

        game_vc_overwrites = game_vcs_category.overwrites

        for player in self.players:
            game_vc_overwrites.update({player: discord.PermissionOverwrite(connect=True)})

        channel_name_prefix = functions.get_info_value('CHANNELNAMEPREFIX', self.guild)
        self.game_vc = await game_vcs_category.create_voice_channel(
            f'{channel_name_prefix}Game#{self.game_id}',
            overwrites=game_vc_overwrites,
            rtc_region=functions.get_info_value('DEFAULTVCREGION', self.guild)
        )
        self.game_vc_id = self.game_vc.id

        self.update_db()

        for player in self.players:
            try:
                await player.edit(voice_channel=self.game_vc)
            except discord.HTTPException:
                pass


class Rank:
    def __init__(self, role_id: int,
                 starting_elo: int,
                 ending_elo: int,
                 win_elo: int,
                 lose_elo: int,
                 mvp_elo: int,
                 role_color: int,
                 guild: discord.Guild):
        self.role_id: int = role_id
        self.starting_elo: int = starting_elo
        self.ending_elo: int = ending_elo
        self.win_elo: int = win_elo
        self.lose_elo: int = lose_elo
        self.mvp_elo: int = mvp_elo
        self.role_color: int = role_color
        self.guild: discord.Guild = guild

    @classmethod
    def from_tuple(cls, __tuple: tuple, guild: discord.Guild):
        return cls(
            __tuple[0],
            __tuple[1],
            __tuple[2],
            __tuple[3],
            __tuple[4],
            __tuple[5],
            __tuple[6],
            guild
        )


class Card:
    def __init__(self, card_name: str,
                 card_file_name: str,
                 discord_name: list,
                 ign: list,
                 elo: list,
                 daily_elo: list,
                 wins: list,
                 losses: list,
                 streak: list,
                 mvps: list,
                 games_played: list,
                 wlr: list,
                 winrate: list,
                 games: list,
                 rank: list,
                 rank_icon: list,
                 skin: list,
                 guild: discord.Guild
                 ):
        self.card_name: str = card_name
        self.card_file_name: str = card_file_name
        self.discord_name: list = discord_name
        self.ign: list = ign
        self.elo: list = elo
        self.daily_elo: list = daily_elo
        self.wins: list = wins
        self.losses: list = losses
        self.streak: list = streak
        self.mvps: list = mvps
        self.games_played: list = games_played
        self.wlr: list = wlr
        self.winrate: list = winrate
        self.games: list = games
        self.rank: list = rank
        self.rank_icon: list = rank_icon
        self.skin: list = skin

        self.card_file_type = self.card_file_name.split(".")[-1]

    @classmethod
    def from_tuple(cls, __tuple: tuple[str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str],
                   guild: discord.Guild):
        card_name: str = __tuple[0]
        card_file_name: str = __tuple[1]

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        discord_name: list = __tuple[2].split(",") if __tuple[2] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        ign: list = __tuple[3].split(",") if __tuple[3] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y
        elo: list = __tuple[4].split(",") if __tuple[4] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,positive_color(int),negative_color(int),zero_color(int)
        daily_elo: list = __tuple[5].split(
            ",") if __tuple[5] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        wins: list = __tuple[6].split(",") if __tuple[6] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        losses: list = __tuple[7].split(",") if __tuple[7] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,positive_color(int),negative_color(int),zero_color(int)
        streak: list = __tuple[8].split(
            ",") if __tuple[8] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        mvps: list = __tuple[9].split(",") if __tuple[9] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        games_played: list = __tuple[10].split(",") if __tuple[10] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        wlr: list = __tuple[11].split(",") if __tuple[11] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        winrate: list = __tuple[12].split(",") if __tuple[12] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,mvp_and_win_color(int),win_color(int),lose_color(int),void_color(int),default_color(int),mvp_and_win_icon_url,win_icon_url,lose_icon_url,void_icon_url
        games: list = __tuple[13].split(
            ",") if __tuple[13] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,color(int)
        rank: list = __tuple[14].split(",") if __tuple[14] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y
        rank_icon: list = __tuple[15].split(",") if __tuple[15] != '' else None

        # box_start_x,box_start_y,box_end_x,box_end_y,default_ign
        skin: list = __tuple[16].split(",") if __tuple[16] != '' else None

        return cls(
            card_name,
            card_file_name,
            discord_name,
            ign,
            elo,
            daily_elo,
            wins,
            losses,
            streak,
            mvps,
            games_played,
            wlr,
            winrate,
            games,
            rank,
            rank_icon,
            skin,
            guild
        )


class ScoredGame:
    def __init__(self,
                 game_id: int,
                 winner: int,
                 team1_elo_changes: list[tuple[int, int]],
                 team2_elo_changes: list[tuple[int, int]],
                 mvps_ids: list[int],
                 scored_by: int,
                 guild: discord.Guild,
                 bot: Optional[commands.Bot] = None
                 ):
        self.game_id: int = game_id
        self.winner: int = winner
        self.loser: int = 1 if winner == 2 else 2
        self.team1_elo_changes: list[tuple[int, int]] = team1_elo_changes
        self.team2_elo_changes: list[tuple[int, int]] = team2_elo_changes
        self.mvps_ids: list[int] = mvps_ids
        self.scored_by: int = scored_by

        self.guild = guild
        self.bot = bot

    @property
    def winner_team_ids(self):
        return [t[0] for t in self.team1_elo_changes] if self.winner == 1 else [t[0] for t in self.team2_elo_changes]

    @property
    def loser_team_ids(self):
        return [t[0] for t in self.team1_elo_changes] if self.winner == 2 else [t[0] for t in self.team2_elo_changes]

    @classmethod
    def from_game_id(cls, game_id: int, guild: discord.Guild, bot: Optional[commands.Bot] = None) -> Self | None:
        db, cursor = functions.database(guild.id)

        scored_game_tuple = cursor.execute("SELECT * FROM scored_games WHERE game_id=?",
                                           (game_id,)).fetchone()

        if scored_game_tuple is None:
            return None

        return cls.from_game_tuple(scored_game_tuple, guild, bot)

    @classmethod
    def from_game_tuple(cls, __tuple: tuple, guild: discord.Guild, bot: Optional[commands.Bot] = None) -> Self:
        # team1_infos = [int(t) for t in __tuple[2].split(",")]
        # team1_ids = team1_infos[:len(team1_infos) // 2]
        # team1_elo_changes = team1_infos[len(team1_infos) // 2:]
        # team1_ids_elo_changes = [(team1_ids[i], team1_elo_changes[i]) for i in range(len(team1_infos) // 2)]
        team1_ids_elo_changes = []
        team1_db_elo_changes_split = __tuple[2].split(',')
        for i, player_id in enumerate(team1_db_elo_changes_split):
            if i % 2 != 0:
                continue
            else:
                team1_ids_elo_changes.append((int(player_id), int(team1_db_elo_changes_split[i + 1])))

        # team2_infos = [int(t) for t in __tuple[3].split(",")]
        # team2_ids = team2_infos[:len(team2_infos) // 2]
        # team2_elo_changes = team2_infos[len(team2_infos) // 2:]
        # team2_ids_elo_changes = [(team2_ids[i], team2_elo_changes[i]) for i in range(len(team2_infos) // 2)]
        team2_ids_elo_changes = []
        team2_db_elo_changes_split = __tuple[3].split(',')
        for i, player_id in enumerate(team2_db_elo_changes_split):
            if i % 2 != 0:
                continue
            else:
                team2_ids_elo_changes.append((int(player_id), int(team2_db_elo_changes_split[i + 1])))

        return cls(
            int(__tuple[0]),
            int(__tuple[1]),
            team1_ids_elo_changes,
            team2_ids_elo_changes,
            [int(t) for t in __tuple[4].split(",")] if __tuple[4] != "" and __tuple[4] is not None else [],
            __tuple[5],
            guild,
            bot
        )

    async def void_game(self, voided_by: discord.Member):
        game = Game.from_game_id(self.game_id, self.guild, self.bot)
        if game.status == "SCORED":
            for team1_player_elo_change in self.team1_elo_changes:
                team1_player = NewPlayer.from_player_id(team1_player_elo_change[0], self.guild)
                team1_player.elo -= team1_player_elo_change[1]
                if self.winner == 1:
                    team1_player.wins -= 1
                else:
                    team1_player.losses -= 1
                if team1_player.player_id in self.mvps_ids:
                    team1_player.mvps -= 1

            for team2_player_elo_change in self.team2_elo_changes:
                team2_player = NewPlayer.from_player_id(team2_player_elo_change[0], self.guild)
                team2_player.elo -= team2_player_elo_change[1]
                if self.winner == 2:
                    team2_player.wins -= 1
                else:
                    team2_player.losses -= 1
                if team2_player.player_id in self.mvps_ids:
                    team2_player.mvps -= 1

            game.status = "SUBMITTED"

            game.update_db()

            db, cursor = functions.database(self.guild.id)

            cursor.execute("DELETE FROM scored_games WHERE game_id=?",
                           (self.game_id, ))
            db.commit()

            scoring_channel = await functions.fetch_channel("SCORING", self.guild)

            webhook = await functions.fetch_webhook(scoring_channel, self.bot)

            await webhook.send(
                embed=functions.embed(
                    self.guild,
                    "Scoring System",
                    f"Voided Game#{self.game_id}",
                    embed_color="ERROR",
                    embed_fields=[
                        ["Team 1", "\n".join(
                            [f"<@{t[0]}> `({'+' if t[1] <= 0 else '-'}){abs(t[1])}` " for t in self.team1_elo_changes]),
                         False],
                        ["Team 2", "\n".join(
                            [f"<@{t[0]}> `({'+' if t[1] <= 0 else '-'}){abs(t[1])}` " for t in self.team2_elo_changes]),
                         False],
                    ],
                    embed_footer_text=f"Undone by {voided_by.name}",
                    embed_timestamp=True
                )
            )

            for player_id in [t[0] for t in self.team1_elo_changes] + [t[0] for t in self.team2_elo_changes]:
                try:
                    member = await functions.fetch_member(player_id, self.guild)
                    await functions.fix(member, nick_check=True, rank_check=True)
                except:
                    pass
            del self
        else:
            raise errors.ScoringError(f"You cannot void this game in its' current state.")


class WeeklyDaily:
    @staticmethod
    def create_daily_weekly_stats(player_id: int, db: sqlite3.Connection):
        if db.cursor().execute("SELECT * FROM daily WHERE id=?", (player_id,)).fetchone() is None:
            db.cursor().execute("INSERT INTO daily VALUES (?, ?, ?, ?, ?, ?)",
                                (player_id, 0, 0, 0, 0, 0))
            db.commit()

        if db.cursor().execute("SELECT * FROM weekly WHERE id=?", (player_id,)).fetchone() is None:
            db.cursor().execute("INSERT INTO weekly VALUES (?, ?, ?, ?, ?, ?)",
                                (player_id, 0, 0, 0, 0, 0))
            db.commit()

    @staticmethod
    def elo(player_id: int, elo_change: int, db: sqlite3.Connection):
        WeeklyDaily.create_daily_weekly_stats(player_id, db)
        daily_elo = db.cursor().execute("SELECT elo FROM daily WHERE id=?",
                                        (player_id,)).fetchone()[0]
        weekly_elo = db.cursor().execute("SELECT elo FROM weekly WHERE id=?",
                                         (player_id,)).fetchone()[0]

        db.cursor().execute("UPDATE daily SET elo=? WHERE id=?",
                            (daily_elo + elo_change, player_id))
        db.commit()
        db.cursor().execute("UPDATE weekly SET elo=? WHERE id=?",
                            (weekly_elo + elo_change, player_id))
        db.commit()

    @staticmethod
    def wins(player_id: int, wins_change: int, db: sqlite3.Connection):
        WeeklyDaily.create_daily_weekly_stats(player_id, db)
        daily_wins = db.cursor().execute("SELECT wins FROM daily WHERE id=?",
                                         (player_id,)).fetchone()[0]
        weekly_wins = db.cursor().execute("SELECT wins FROM weekly WHERE id=?",
                                          (player_id,)).fetchone()[0]

        db.cursor().execute("UPDATE daily SET wins=? WHERE id=?",
                            (daily_wins + wins_change, player_id))
        db.commit()
        db.cursor().execute("UPDATE weekly SET wins=? WHERE id=?",
                            (weekly_wins + wins_change, player_id))
        db.commit()

    @staticmethod
    def losses(player_id: int, losses_change: int, db: sqlite3.Connection):
        WeeklyDaily.create_daily_weekly_stats(player_id, db)
        daily_losses = db.cursor().execute("SELECT losses FROM daily WHERE id=?",
                                           (player_id,)).fetchone()[0]
        weekly_losses = db.cursor().execute("SELECT losses FROM weekly WHERE id=?",
                                            (player_id,)).fetchone()[0]

        db.cursor().execute("UPDATE daily SET losses=? WHERE id=?",
                            (daily_losses + losses_change, player_id))
        db.commit()
        db.cursor().execute("UPDATE weekly SET losses=? WHERE id=?",
                            (weekly_losses + losses_change, player_id))
        db.commit()

    @staticmethod
    def mvps(player_id: int, mvps_change: int, db: sqlite3.Connection):
        WeeklyDaily.create_daily_weekly_stats(player_id, db)
        daily_mvps = db.cursor().execute("SELECT mvps FROM daily WHERE id=?",
                                         (player_id,)).fetchone()[0]
        weekly_mvps = db.cursor().execute("SELECT mvps FROM weekly WHERE id=?",
                                          (player_id,)).fetchone()[0]

        db.cursor().execute("UPDATE daily SET mvps=? WHERE id=?",
                            (daily_mvps + mvps_change, player_id))
        db.commit()
        db.cursor().execute("UPDATE weekly SET mvps=? WHERE id=?",
                            (weekly_mvps + mvps_change, player_id))
        db.commit()

    @staticmethod
    def games_played(player_id: int, games_played_change: int, db: sqlite3.Connection):
        WeeklyDaily.create_daily_weekly_stats(player_id, db)
        daily_games_played = db.cursor().execute("SELECT games_played FROM daily WHERE id=?",
                                                 (player_id,)).fetchone()[0]
        weekly_games_played = db.cursor().execute("SELECT games_played FROM weekly WHERE id=?",
                                                  (player_id,)).fetchone()[0]

        db.cursor().execute("UPDATE daily SET games_played=? WHERE id=?",
                            (daily_games_played + games_played_change, player_id))
        db.commit()
        db.cursor().execute("UPDATE weekly SET games_played=? WHERE id=?",
                            (weekly_games_played + games_played_change, player_id))
        db.commit()


class Party:
    def __init__(self, leader_id: int,
                 members_ids: list[int],
                 created_at: int,
                 last_queued: int,
                 autowarp: bool,
                 party_limit: int,
                 guild: discord.Guild):
        self.leader_id: int = leader_id
        self.members_ids: list[int] = members_ids
        self.created_at: int = created_at
        self._last_queued: int = last_queued
        self._autowarp: bool = autowarp
        self.party_limit: int = party_limit
        self.guild = guild

    def __eq__(self, other):
        if self.leader_id == getattr(other, 'leader_id', None):
            return True
        else:
            return False

    async def update_leader_games_count(self, bot: commands.Bot):
        leader = await self.guild.fetch_member(self.leader_id)
        if [t.id for t in leader.roles if t.id in functions.get_info_value("PERMENANTPARTYROLESIDS", self.guild)]:
            return

        db, cursor = functions.database(self.guild.id)
        old_games_count = cursor.execute("SELECT games_count FROM party_games WHERE player_id=?",
                                         (self.leader_id, )).fetchone()
        if old_games_count is None:
            await self.disband(bot, 'No more party games')
            return
        new_games_count = old_games_count[0] - 1
        cursor.execute("UPDATE party_games SET games_count=? WHERE player_id=?",
                       (new_games_count, self.leader_id))
        db.commit()

        if new_games_count <= 0:
            await self.disband(bot, 'No more party games')
            return

    @property
    def all_members(self):
        return [self.leader_id] + self.members_ids

    @property
    def lastqueued(self):
        return self._last_queued

    @lastqueued.setter
    def lastqueued(self, value: int):
        db, cursor = functions.database(self.guild.id)

        self._last_queued = value

        cursor.execute("UPDATE parties SET last_queued=? WHERE leader_id=?",
                       (value, self.leader_id))
        db.commit()

    @property
    def autowarp(self):
        return self._autowarp

    @autowarp.setter
    def autowarp(self, value: bool):
        self._autowarp = value

        db, cursor = functions.database(self.guild.id)

        cursor.execute("UPDATE parties SET autowarp=? WHERE leader_id=?",
                       (1 if value else 0, self.leader_id))
        db.commit()

    @classmethod
    def from_tuple(cls, __party_tuple: tuple, guild: discord.Guild):
        leader_id, members_ids_not_split, created_at, last_queued, autowarp, party_limit = __party_tuple
        members_ids = [int(t) for t in members_ids_not_split.split(",")] \
            if members_ids_not_split != '' and members_ids_not_split is not None \
            else []
        return cls(leader_id, members_ids, created_at, last_queued, True if autowarp else False, party_limit, guild)

    @classmethod
    def from_leader_id(cls, leader_id: int, guild: discord.Guild):
        db, cursor = functions.database(guild.id)

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=?",
                                     (leader_id,)).fetchone()
        if party_tuple is None:
            return None
        else:
            return cls.from_tuple(party_tuple, guild)

    def __len__(self):
        return len(self.members_ids) + 1

    def fetch_new_data_from_database(self):
        db, cursor = functions.database(self.guild.id)

        party_tuple = cursor.execute("SELECT * FROM parties WHERE leader_id=? AND created=?",
                                     (self.leader_id, self.created_at)).fetchone()
        if party_tuple is None:
            raise errors.PartyError(f"This party doesn't exist anymore.")

        leader_id, members_ids_not_split, created_at, last_queued, autowarp, party_limit = party_tuple
        members_ids = [int(t) for t in members_ids_not_split.split(",")] \
            if members_ids_not_split != '' and members_ids_not_split is not None \
            else []

        self.__init__(leader_id, members_ids, created_at, last_queued, True if autowarp else False, party_limit,
                      self.guild)
        return None

    async def add_party_member(self, member_id: int, bot: commands.Bot):
        self.fetch_new_data_from_database()

        if member_id in self.members_ids:
            raise errors.PartyError(f"Player(<@{member_id}>) is already in <@{self.leader_id}>s' party.")

        if len(self) + 1 > self.party_limit:
            raise errors.PartyError(
                f"you cannot join Player(<@{self.leader_id})>s' party since it has the maximum amount of players.")

        db, cursor = functions.database(self.guild.id)

        self.members_ids.append(member_id)

        cursor.execute("UPDATE parties SET members_ids=? WHERE leader_id=?",
                       (','.join([str(t) for t in self.members_ids]), self.leader_id))
        db.commit()
        cursor.execute("INSERT INTO party_members VALUES (?, ?)",
                       (self.leader_id, member_id))
        db.commit()

        return None

    async def remove_party_member(self, member_id: int, bot: commands.Bot):
        self.fetch_new_data_from_database()

        if member_id == self.leader_id:
            await self.disband(bot)
            return

        if member_id not in self.members_ids:
            raise errors.PartyError(f"Player(<@{member_id}>) is not in <@{self.leader_id}>s' party.")

        db, cursor = functions.database(self.guild.id)

        self.members_ids.remove(member_id)

        cursor.execute("UPDATE parties SET members_ids=? WHERE leader_id=?",
                       (','.join([str(t) for t in self.members_ids]), self.leader_id))
        db.commit()
        cursor.execute("DELETE FROM party_members WHERE member_id=?",
                       (member_id,))
        db.commit()

        await self.disband_if_possible(bot)

        return None

    async def disband(self, bot: commands.Bot, reason: Optional[str] = None):
        db, cursor = functions.database(self.guild.id)
        cursor.execute("DELETE FROM parties WHERE leader_id=?",
                       (self.leader_id,))
        db.commit()

        cursor.execute("DELETE FROM party_members WHERE leader_id=?",
                       (self.leader_id,))
        db.commit()

        cursor.execute("DELETE FROM party_invites WHERE leader_id=?",
                       (self.leader_id,))
        db.commit()

        party_alerts_channel = await functions.fetch_channel('PARTYALERTS', self.guild)
        party_alerts_channel_webhook = await functions.fetch_webhook(party_alerts_channel, bot)

        await party_alerts_channel_webhook.send(
            content=''.join([f"<@{self.leader_id}>"] + [f"<@{t}>" for t in self.members_ids]),
            embed=functions.embed(
                self.guild,
                'Party System',
                f'Your party has been disbanded.' + \
                ('' if reason is None else f"\n**Reason:** {reason}"),
                embed_color=0
            )
        )

    async def warp(self, channel: discord.VoiceChannel):
        for party_member_id in self.members_ids:
            try:
                party_member = await functions.fetch_member(party_member_id, self.guild)
                if party_member.voice is not None:
                    await party_member.edit(voice_channel=channel,
                                            reason=f"Warping party of {self.leader_id}")
            except discord.HTTPException:
                pass

    async def disband_if_possible(self, bot: commands.Bot):
        if len(self.members_ids) == 0:
            db, cursor = functions.database(self.guild.id)
            if cursor.execute("SELECT * FROM party_invites WHERE leader_id=?",
                              (self.leader_id,)).fetchone() is None:
                await self.disband(bot)
        elif datetime.datetime.fromtimestamp(self.lastqueued) + datetime.timedelta(hours=1) <= datetime.datetime.now():
            await self.disband(bot, 'Inactivity')
            return
