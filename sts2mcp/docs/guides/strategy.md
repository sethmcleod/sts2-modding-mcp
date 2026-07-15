# Slay the Spire 2 — Gameplay & Balance Primer

A working model of what *good* Slay the Spire 2 play looks like. Two uses:

1. **Piloting playtests** — when you (or an agent) drive a run via the bridge, these
   heuristics get you deeper into a run so more of a mod's content actually gets exercised.
2. **Judging mod balance** — to tell whether a modded card/relic is over- or under-tuned,
   you need a baseline for what a fair card is *worth*. That baseline is here.

> [!IMPORTANT]
> This is a heuristic primer, not a solver. STS2 is a deep game; treat everything below as
> a strong default, not a rule. When a specific board contradicts a heuristic, trust the board.

> [!CAUTION]
> **AutoSlay is not a balance signal.** `AutoSlayCardSelector` shuffles the reward options
> and picks *randomly*, not strategically (see [autoslay.md](autoslay.md)). It is a
> stability/crash tool — it will happily build an incoherent deck. To evaluate whether a
> card is too strong or too weak, drive the run yourself (bridge actions / `run_test_scenario`)
> and apply the judgment below. See [testing.md](testing.md).

## Core principles

- **HP is a resource, not a score.** You don't win by ending fights at full health — you win
  by reaching the act boss with enough deck and enough HP to survive it. Taking a few hits to
  end a fight a turn sooner is usually correct.
- **Deck quality beats deck size.** Every non-synergistic card you add dilutes the odds of
  drawing your key cards. Skipping a card reward is a real, common, correct choice.
- **Front-load damage.** Killing an enemy removes *all* of its future damage. Focus one target
  to death rather than spreading chip damage, unless an AoE payoff says otherwise.
- **Tempo compounds.** Debuffs (Vulnerable/Weak/poison), Strength, and block-scaling all pay
  off more the earlier they land. Setup on turn 1 is worth more than the same setup on turn 4.
- **Energy is the real currency.** Damage-per-energy and block-per-energy are how you compare
  cards, not raw numbers. A 3-cost that does what two 1-costs do is usually worse (less
  flexible, harder to fit in a turn).

## Combat sequencing

Within a turn, a good default order:

1. **0-cost / setup first** — card draw, energy, cost reducers, "when you play a card" enablers.
   They cost nothing and change what the rest of the turn can do.
2. **Debuffs and buffs before attacks** — apply Vulnerable/Weak and gain Strength *before* the
   attacks that should benefit from them.
3. **Biggest attacks last** — so they ride the accumulated Strength/Vulnerable.
4. **Check for lethal before you block.** If you can kill everything this turn, block is wasted
   energy. Read enemy HP every turn — it re-rolls per run, so don't assume.

## Reading enemy intents

Intent is the single most important read each turn:

- **Attack** → you need block (or lethal). Block roughly to the incoming number; slight
  under-block is fine if you're racing.
- **Buff / Sleep / no attack** → go all-in on offense; don't waste energy on block.
- **Debuff** → decide if the debuff matters this fight; often you can eat it and keep attacking.
- **Multi-hit** intents interact with block per hit — flat block is weaker against many small
  hits; per-hit mitigation (thorns, Weak) is stronger.

## Map & pathing

You usually pick the path, not just the next room:

- **Elites** give the best relics but hit hard — take them when healthy (well above half HP) and
  when your deck has a plan. Early relics snowball; a skipped early elite is a missed engine.
- **Rest sites** — rest to heal before a boss or elite when low; use the site's upgrade/other
  options when your HP is comfortable. Plan so a rest lands *before* the act boss if you're hurt.
- **Unknowns** are variance — generally safer than elites at medium HP, but not free.
- **Shops** are worth routing to with gold to spend (≈100+); a good relic or a card-removal is
  often the highest-value purchase.
- **Card removal** is one of the strongest shop effects — thinning the starter filler raises
  every future draw.

## Elites, bosses, and scaling

- **Longer fights favor the enemy** in scaling fights — many elites/bosses ramp Strength or
  stack intent over time. Race them when you can; don't settle into a block-forever stance
  against something that out-scales you.
- **Kill the leader** in multi-enemy fights where minions depend on it; minions often flee or
  weaken when the leader dies.
- **Spend potions on hard fights.** They don't carry between acts — hoarding a potion into the
  next act throws away value. An unused potion at a boss kill is a mistake.

## Potions

- Use potions **proactively** on elites/bosses, not as a last-resort panic button.
- Prefer using a permanent-value or setup potion **early** in a fight where it enables a bigger
  turn, rather than saving it "just in case."
- Belt space is limited — if the belt is full and a better potion is offered, use or discard the
  weakest one rather than skipping the reward.

## Card rewards & deck building

- **Have a plan by end of Act 1.** Ask "what does this deck *do*?" and take cards that advance
  that answer; skip cards that don't.
- **Curve matters.** A deck of all 2–3 cost cards floods your energy; you need cheap enablers to
  actually play your expensive payoffs.
- **Redundancy over greed.** Two copies of a good common that you draw reliably often beat one
  flashy rare you rarely see.

## Common mistakes (to avoid, and to watch for when piloting)

- Over-blocking against buffing/sleeping enemies.
- Adding every card offered → bloated deck that never draws its wins.
- Hoarding potions into the next act (they're lost).
- Assuming enemy HP from a previous run — rosters re-roll (see [testing.md](testing.md)).
- Blocking when lethal was available.
- Fighting an elite at low HP with no plan for the incoming burst.

## Using this to judge mod balance

When evaluating a modded card, compare it to what a fair card of its rarity/cost is *worth* in
energy terms. Rough single-target baselines (treat as ballpark, not spec):

- **Attacks:** on the order of ~6–8 damage per energy for a common; rares buy more per energy but
  usually attach a cost, condition, or downside.
- **Block:** on the order of ~5–8 block per energy for a common.
- **Starter strikes/defends** sit *below* that curve on purpose — they're filler you want to thin.
- **0-cost cards** have no opportunity cost (you can play any number per turn), so "free" effects
  and card-generation are worth more than their printed numbers suggest — scrutinize them harder.

Red flags when piloting a modded run: a single card that trivializes elites, an engine that goes
infinite, block that outpaces all incoming damage for free, or scaling with no ceiling. Green
flags: the card is strong *in its archetype* and mediocre outside it, and it competes with — not
strictly dominates — the base-game cards of the same slot.

> [!TIP]
> Pair this with `run_test_scenario` for reproducible balance checks: fix a seed, hand the deck a
> specific modded card, and assert the damage/block/HP outcome against these baselines. See
> [testing.md](testing.md).
