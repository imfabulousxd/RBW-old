import discord

import classes


def refresh_view(view: discord.ui.View, game: classes.Game):
    disabled_items_custom_ids = []
    disabled_items_labels = []
    disabled_items_emojis = []
    if game.is_scored():
        disabled_items_custom_ids.extend([
            "button:winnerteam1",
            "button:winnerteam2",
            "button:done",
            "select:mvps"
        ])
        disabled_items_labels.extend([
            '1',
            '2',
            "Select MVP(s) ..."
        ])
        disabled_items_emojis.extend([
            '✅'
        ])
    elif game.status == "SUBMITTED":
        disabled_items_custom_ids.extend([

        ])
    elif game.status == "VOIDED":
        disabled_items_custom_ids.extend([
            "button:void",
            "button:winnerteam1",
            "button:winnerteam2",
            "button:done",
            "select:mvps"
        ])
        disabled_items_labels.extend([
            "1",
            "2",
            "Select MVP(s) ..."
        ])
        disabled_items_emojis.extend([
            '✅',
            "🟥"
        ])

    for i, child in enumerate(view.children):
        if isinstance(child, discord.ui.Button):
            if (
                    child.custom_id.endswith(tuple(disabled_items_custom_ids)) or
                    child.label in disabled_items_labels or
                    getattr(child.emoji, 'name', None) in disabled_items_emojis
            ):
                view.children[i].disabled = True
            else:
                view.children[i].disabled = False
        elif isinstance(child, discord.ui.Select):
            if (
                    child.custom_id.endswith(tuple(disabled_items_custom_ids)) or
                    child.placeholder in disabled_items_labels
            ):
                view.children[i].disabled = True
            else:
                view.children[i].disabled = False
        elif isinstance(child.item, discord.ui.Button):
            if (
                    child.item.custom_id.endswith(tuple(disabled_items_custom_ids)) or
                    child.item.label in disabled_items_labels or
                    getattr(child.item.emoji, 'name', None) in disabled_items_emojis
            ):
                view.children[i].item.disabled = True
            else:
                view.children[i].item.disabled = False
        elif isinstance(child.item, discord.ui.Select):
            if (
                    child.item.custom_id.endswith(tuple(disabled_items_custom_ids)) or
                    child.item.placeholder in disabled_items_labels
            ):
                view.children[i].item.disabled = True
            else:
                view.children[i].item.disabled = False


async def refresh_message(interaction: discord.Interaction, game: classes.Game, view: discord.ui.View):
    refresh_view(view, game)
    await interaction.message.edit(
        embed=await game.game_scoring_embed(),
        view=view
    )
