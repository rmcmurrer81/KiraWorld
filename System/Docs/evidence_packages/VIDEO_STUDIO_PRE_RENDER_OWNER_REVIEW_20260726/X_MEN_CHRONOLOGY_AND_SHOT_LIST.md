# X-Men chronological chapter and shot plan

All timecodes are source-relative and must be checked in the Studio player
before approval. “NARRATION” means source muted. “SOURCE” means Robert pauses.
“DUCK -18 dB” means source is deliberately present under Robert. No source is
used in more than one chapter.

| Ch | Timeline / purpose | Shot, exact source and in/out | Audio mode |
|---|---|---|---|
| 1 | 2000, establish original team | Official *X-Men* key art and credited cast card, 00:00–00:18; custom timeline 2000, 00:18–00:35; licensed/approved stills of Wolverine, Rogue, Xavier, Magneto, each 6–8s | NARRATION |
| 2 | 2003, mansion becomes a target | `official_xmen/KNIdceH7XOw.mp4` (*X2*, 20th Century), 00:46–01:01 mansion threat; Xavier/Magneto relationship stills 01:01–01:24; Alkali Lake location card 01:24–01:35 | SOURCE 00:46–00:53, then DUCK -18 dB |
| 3 | 2006, cure and Phoenix plots | Official key art, cure-vial close-up and two-column “cure / Phoenix” diagram, 00:00–00:38; Alcatraz geography diagram, 00:38–00:55 | NARRATION; no unrelated trailer |
| 4 | 2009, Logan’s explained past | `official_xmen/kd6zYnHwQWA.mp4` (*Origins*, 20th Century), 00:27–00:39 war montage and 01:10–01:22 adamantium; continuity-card comparison 00:24 | DUCK -18 dB; no raw dialogue |
| 5 | 1962 / 2011, Charles and Erik | `official_xmen/XKF6J6kgs0s.mp4` (*First Class*, 20th Century UK), 00:31–00:45 recruitment, 01:38–01:50 beach conflict; 1962 timeline map 00:20 | SOURCE for first 4s of recruitment, then DUCK -18 dB |
| 6 | 2013, Logan in Japan | `official_xmen/u1VCP3O8wG0.mp4` (*The Wolverine*, 20th Century), 00:34–00:47 Japan/train and 01:28–01:40 mortality conflict; Jean/Logan loss card 00:16 | DUCK -18 dB |
| 7 | 1973 / 2014, timeline reset | Owner clip `QuickSilver Kitchen Scene - X-Men Days Of Future Past (2014) Movie Clip HD.mp4`, 00:31–00:54; official `gsjtg7m1MMM.mp4`, 00:42–00:55 ruined future; animated original/revised timeline 00:45 | SOURCE for owner clip; DUCK -18 dB trailer; NARRATION diagram |
| 8A | 2016, *Deadpool* | Approved official poster/key art; Wade/Colossus relationship card; no unverified clip until exact official source approved | NARRATION |
| 8B | 1983 / 2016, *Apocalypse* | Owner clip `Quicksilver Saves Everyone - Sweet Dreams - X-Men Apocalypse (2016) Movie Clip HD.mp4`, 00:54–01:24; official `PfBVIHgQbYk.mp4`, 01:04–01:16 younger team | SOURCE for rescue; DUCK -18 dB trailer |
| 9 | 2029 / 2017, *Logan* | `official_xmen/Div0iP65aZo.mp4`, 00:13–00:31 quiet Logan/Charles/Laura, 01:21–01:38 pursuit; family/legacy diagram 00:22 | SOURCE 00:13–00:19, then DUCK -18 dB |
| 10 | 2018, *Deadpool 2* | Owner clip `Deadpool Travels Back In Time - Wolverine Cameo - Post Credit Scene - Deadpool 2 (2018).mp4`, 00:48–01:07; Cable/Firefist story card 00:20 | SOURCE; Robert pauses for punch line |
| 11A | 1992 / 2019, *Dark Phoenix* | `official_xmen/azvR__GRQic.mp4`, 00:22–00:34 space rescue and 01:17–01:29 Jean conflict; release-era timeline 00:18 | DUCK -18 dB |
| 11B | 2020, *New Mutants* | `official_xmen/W_vJhUAOFpI.mp4`, 00:36–00:50 institution/horror setup and 01:15–01:27 team; Fox-era closing card 00:18 | DUCK -18 dB |
| 12 | MCU multiverse returns | Official Marvel still cards for Stewart in *Multiverse of Madness* and Beast in *The Marvels*; `official_xmen/73_1biulkYk.mp4` (*Deadpool & Wolverine*, Marvel), 00:43–00:57 TVA and 01:20–01:34 Logan reveal; branch diagram 00:35 | NARRATION stills/diagram; DUCK -18 dB trailer |
| 13 | Confirmed *Doomsday* facts | Marvel official cast-announcement page captured with URL/date, slow pan 00:20; individual credited headshots 5s each; confirmed/unconfirmed split card 00:25; official release page 00:12 | NARRATION only |
| 14 | Conclusion | Full animated 2000–2026 branch timeline 00:55; one different approved still per era, 4s each; final title 00:10 | NARRATION, then intentional music-free 1s tail |

## Render exclusions and acceptance

- Any clip without exact approved source and in/out remains a blank storyboard
  decision, not an automatically substituted trailer.
- The *Deadpool* chapter presently has no approved video clip and therefore uses
  approved still/key-art material until Robert selects a source.
- Each planned segment receives `narration_required`, `source_audio_mode`, and
  `source_id`. The renderer refuses a missing narration asset.
- Target mix: Robert -9.5 dB approved profile; source under narration -18 dB
  relative; no normalization changes to Robert’s pitch.
- Final acceptance: audio/video duration delta ≤0.10s; independent decode of
  both streams to EOF; zero AAC decode errors; silence intervals >1.5s require
  an intentional marker; no source ID above two appearances; complete real-time
  watch and chapter sign-off by Robert.
