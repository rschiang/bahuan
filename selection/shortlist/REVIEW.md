# Era selection review

Draft manifest: `selection/selection.toml`. Resolved: 3963 emoji. android-7.1 1630,
android-12 1567, latest 504, waveflag 262. No avoided eras used, no mixed styles
inside a family, 7 overrides, 38 redraw items.

`7.1 → 12` is a list value. It pins android-12's 2020 art (unchanged since
android-11 but borderless) ahead of latest for people and animals. Where it changes
anything today: 🧍 🏂 🧘 🦝 🦓 🐻‍❄️ 🪶. Confidence is the shortlist agent's,
except where marked.

## Subgroups

| group | subgroup | era | conf |
|---|---|---|---|
| Smileys & Emotion | face-smiling | 7.1 | high |
|  | face-affection | 7.1 | high |
|  | face-tongue | 7.1 | high |
|  | face-hand | 7.1 | medium |
|  | face-neutral-skeptical | 7.1 | medium |
|  | face-sleepy | 7.1 | high |
|  | face-unwell | 7.1 | medium |
|  | face-hat | 7.1 | medium |
|  | face-glasses | 7.1 | high |
|  | face-concerned | 7.1 | high |
|  | face-negative | 7.1 | high |
|  | face-costume | 7.1 | high |
|  | cat-face | 7.1 | high |
|  | monkey-face | 7.1 | high |
|  | heart | 7.1 | medium |
|  | emotion | 7.1 | high |
| People & Body | hand-fingers-open | 7.1 | medium |
|  | hand-fingers-partial | 7.1 | medium |
|  | hand-single-finger | 7.1 | medium |
|  | hand-fingers-closed | 7.1 | medium |
|  | hands | 7.1 | medium |
|  | hand-prop | 7.1 | high |
|  | body-parts | 7.1 | medium |
|  | person | 7.1 → 12 | medium |
|  | person-gesture | 7.1 → 12 | high |
|  | person-role | 12 | medium (changed) |
|  | person-fantasy | 12 | medium |
|  | person-activity | 7.1 → 12 | high |
|  | person-sport | 7.1 → 12 | high |
|  | person-resting | 7.1 → 12 | medium |
|  | family | 7.1 → 12 | medium |
|  | person-symbol | 12 | medium |
| Animals & Nature | animal-mammal | 7.1 → 12 | medium |
|  | animal-bird | 7.1 → 12 | medium |
|  | animal-amphibian | 7.1 | high |
|  | animal-reptile | 7.1 → 12 | high |
|  | animal-marine | 7.1 → 12 | medium |
|  | animal-bug | 7.1 → 12 | medium |
|  | plant-flower | 12 | medium |
|  | plant-other | 12 | medium |
| Food & Drink | food-fruit | 12 | high |
|  | food-vegetable | 12 | high |
|  | food-prepared | 12 | high |
|  | food-asian | 12 | medium |
|  | food-sweet | 12 | medium |
|  | drink | 12 | high |
|  | dishware | 7.1 | medium |
| Travel & Places | place-map | 7.1 | medium |
|  | place-geographic | 7.1 | medium |
|  | place-building | 7.1 | medium |
|  | place-religious | 7.1 | medium |
|  | place-other | 7.1 | high |
|  | transport-ground | 7.1 | high |
|  | transport-water | 7.1 | high |
|  | transport-air | 7.1 | high |
|  | hotel | 7.1 | medium |
|  | time | 7.1 | high |
|  | sky & weather | 7.1 | high |
| Activities | event | 7.1 | high |
|  | award-medal | 7.1 | high |
|  | sport | 7.1 | medium |
|  | game | 7.1 | medium |
|  | arts & crafts | 7.1 | medium |
| Objects | clothing | 7.1 | medium |
|  | sound | 7.1 | high |
|  | music | 7.1 | high |
|  | musical-instrument | 7.1 | medium |
|  | phone | 7.1 | high |
|  | computer | 7.1 | high |
|  | light & video | 7.1 | high |
|  | book-paper | 7.1 | medium |
|  | money | 7.1 | high |
|  | mail | 7.1 | high |
|  | writing | 7.1 | high |
|  | office | 7.1 | high |
|  | lock | 7.1 | high |
|  | tool | 7.1 | medium |
|  | science | 7.1 | medium |
|  | medical | 12 | medium |
|  | household | 12 | medium |
|  | other-object | 7.1 | medium |
| Symbols | transport-sign | 7.1 | high |
|  | warning | 7.1 | high |
|  | arrow | 7.1 | high |
|  | religion | 7.1 | high |
|  | zodiac | 7.1 | high |
|  | av-symbol | 7.1 | high |
|  | gender | 7.1 | medium |
|  | math | 7.1 | medium |
|  | punctuation | 7.1 | medium |
|  | currency | 7.1 | high |
|  | other-symbol | 7.1 | medium |
|  | keycap | 7.1 | high |
|  | alphanum | 7.1 | high |
|  | geometric | 7.1 | medium |
| Flags | flag | 7.1 | high |
|  | country-flag | waveflag | high |
|  | subdivision-flag | waveflag | high |

## Owner decisions

- **person-role → android-12 (changed from the agent's 7.1).** Under 7.1, each of the 16 professions shows man/woman in Nougat art and person (🧑‍⚕️ and the others) in different 2020 art, with different props: farmer hat, cook toque, judge chair. The skip rule would now push the person forms to latest, which is a third design. android-12 gives one design per trio, and the gender-neutral form is what keyboards offer first. Cost: 👮 🕵️ 💂 👷 👳 🤴 👸 lose the Nougat look, and 7.1 person-gesture sits next to 2020 person-role. Alternative: `["android-7.1", "android-12"]` plus overrides 👨‍🚀 👩‍🚀 🤰 → android-12 (the agent's reasons: dark visor reads as a skin tone; 7.1 pregnant woman doesn't read at 20px).
- **person stays 7.1 → 12.** 👨 👩 👶 👦 👧 👴 👵 👱 come from 7.1 (60 keys). 🧑 🧒 🧓, beards and hair ZWJs come from 2020 art (108). That is a small gap: eyebrows, closed smile. Alternative: android-12 for the whole subgroup, to match person-role.
- **person-fantasy android-12.** This keeps 🎅 🤶 🧑‍🎄 coherent and now matches person-role. Alternative: override 🎅 🤶 → 7.1 and accept the Mx Claus mismatch.
- **7.1 gendered bases** (💁 🙋 🤦 🤷 = woman, 🙇 🏌️ 🏄 🚴 = man) read as gendered. A fix means leaving 7.1 for the whole family. Not done.
- **Faces: 34 newer faces are latest round flats among blobs** (🥰 🤩 🥺 🥳 🤪 🥴 and others). They are unbordered, so they're not in [redraw], but they are the most visible seam. They're the top optional blob-redraw candidates, led by 🥺 🥰 🤩 🥳.
- **😵 vs 😵‍💫.** Blob 😵 has spiral eyes, the same as the latest 😵‍💫. Keep for nostalgia, or redraw an X-eyed blob.
- **Hearts.** The 7.1 ❤️ is magenta and 🩷 (latest) is light pink, so they read alike. Recolour the 7.1 SVG red. 🩵 🩶 🩷 (latest) are glossy next to the flat 7.1 row, so they're optional redraws.
- **Geometric colour rows.** I kept flat 7.1 🔴 🔵 ⚫ ⚪ ⬛ ⬜ and put the 12 glossy E12 shapes in [redraw]. Alternative if no redraw is planned: override those six to android-12 so the rows match.
- **✅ → android-12** brings a glossy green tile among flat 7.1 symbols. The 7.1 tick is invisible at 20px. Alternative: a flat 7.1-style redraw (cf. ❎).
- **❓ ❗ are blue in 7.1** and ❔ ❕ are very pale. Recolour the 7.1 masters rather than use the glossy android-12 ones.
- **Food 12 / dishware 7.1, plants 12 / animals 7.1.** Kept as reasoned: 12 cutlery is grey gradient, and plants were really redrawn in 2021 while animals weren't. Alternatives: dishware → 12; plants → 7.1. food-asian is where 7.1 holds up best if blob food is wanted.
- **animal-mammal 7.1** puts a navy 🐘 next to the grey 2020 🦣, and a 🦍 face next to the full-body 🦧. Alternative: 12 for the whole subgroup.
- **household and medical 12** (7.1 covers only 7 and 2 items). Alternative: 7.1, a different palette.
- **family 7.1 → 12**: 25 keys from 7.1, 312 from 2020 art. The two look nearly identical. Alternative: 12 for the whole subgroup, to remove the 7.1 gendered vs android-12 toned seam.
- **Small checks the agents flagged:** 🦋 latest (blue) vs the 7.1 orange monarch twin; 🥒 vs 🫛/pickle look alike in 12 (optional 🥒 → latest); 📑 vs 📙 in 7.1; ⛰️ vs 🏔️ in 7.1; ♨️ is blue in 7.1; ☃️ ⛄ are low-contrast in 7.1; 🗿 legibility.

## Redraw backlog (38 in [redraw])

- **Bordered =11, no alternative (19):** ❤️‍🔥 ❤️‍🩹 🧡 🤍 🤎 · 🦾 🦿 🧠 🫀 🫁 🦷 · 🪄 🪆 🪢 · 🪗 · 🪙 · 🩸 🩺 · 🪟 · 🪦. 🫁 and 🩸 are nearly flat and low priority.
- **Flags (2):** 🏳️‍⚧️ 🏴‍☠️. Regenerate through the waveflag pipeline.
- **Keycap tiles (4):** 🧑‍🧑‍🧒 🧑‍🧑‍🧒‍🧒 🧑‍🧒 🧑‍🧒‍🧒 (latest only). Redraw as flat blue busts in the 👥 style.
- **Soft, glossy not bordered (12):** 🟠🟡🟢🟣🟤🟥🟦🟧🟨🟩🟪🟫. Trivial flat shapes.
- **Optional, not in [redraw]:** the round fallback faces (above); ♾️ and 🟰 (bevel tiles in math); 🪯 (purple tile in religion); 🪫 vs the 7.1 🔋 colour; 🫂 (blurry gradient); 🧖 steam; 🪨 shading.

## Dropped/changed agent suggestions

- **Face → latest overrides (20: 🥰 🤩 🥲 🥺 🥱 🤭 🤫 🥳 🥸 🤬 🤨 😶‍🌫️ 😮‍💨 🤪 🤮 🥵 🥶 🥴 😵‍💫 🤯):** dropped. The fallback skip rule already sends these to latest. 🧐 is kept, because its 12 art is a retouch rather than =11.
- **Hand → latest overrides 🤌 🤏 🤟 🤲:** dropped as redundant (skip rule).
- **Body-part → latest overrides 🦵 🦶 🦻 🦴:** dropped as redundant.
- **🩴 🪘 🪧 🪂 → latest:** dropped as redundant.
- **💏 💑 → android-12:** dropped as redundant. 7.1 lacks the toned variants, so the family moves to 12 on its own.
- **👨‍🚀 👩‍🚀 🤰 → android-12:** dropped because person-role is now android-12. Re-add them if person-role goes back to 7.1.
- **person-role 7.1 → android-12:** see Owner decisions.
- **Lists added (person, person-gesture, person-activity, person-sport, person-resting, family, animal-mammal/bird/reptile/marine/bug):** agents assumed fallbacks would use the =11 2020 art. The new skip rule would send 🧍 🏂 🧘 🦝 🦓 🐻‍❄️ 🪶 (and the person-role person forms) to latest, which has contour lines, grey shading or realistic full bodies.
- **Hands, faces, body-parts kept as plain 7.1:** for these the agents wanted latest over the =11 bordered gradient art, so the skip rule is right there.
- **Geometric optional overrides 🔴 🔵 ⚫ ⚪ ⬛ ⬜ → 12:** not applied. Owner decision, see above.
- **🥒 → latest (food-vegetable agent, left out by them too):** not applied.
