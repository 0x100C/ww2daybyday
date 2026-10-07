# WWII Day by Day — Europe, North Africa and the Middle East, 1 Sep 1939 – May 1945

This is a day-by-day animated map of the Second World War in Europe. It is a full rewrite of the earlier Leaflet/GeoJSON project and is built to match the look of the reference video
(<https://www.youtube.com/watch?v=1CqGeAmVu1I>) and `lookwewant.png`. The map has:
- a pale hillshaded terrain with built-up areas as dark texture and no city names;
- flat faction colours;
- white front lines, a lighter band while ground is being taken, and pink national borders;
- rotating dashed markers around encirclements.

## Running it

The app is static: an HTML page, ES modules, prebuilt tiles and a compiled territory stream in `data/`. It needs no build step to run.

```
node server.js            # http://127.0.0.1:3847
# or
python3 -m http.server 8000
```

It needs a browser with WebGL2 (any current Chrome, Edge, Firefox or Safari).

**Controls**
- Space plays or pauses. The slider scrubs, and arrow keys step ±1 day (with Shift, ±7 days).
- Mouse wheel zooms, dragging pans, and ⌂ resets the view.
- Checkboxes toggle fronts, borders, pocket markers and the sea hatch.
- The default speed is **2.6 days/s**, the rate the reference video plays at: about 2,075 days in about 795 s.

**URL parameters**
- `?date=1941-06-22&h=12` jumps to a given date and hour.
- `view=poland` zooms to the Poland crop used in the comparisons.
- `play=1` starts playback.
- `speed=5` sets days per second.

## Rebuilding the data (optional)

You need Python 3.10+ with `numpy`, `scipy`, `scikit-image`, `Pillow` and `shapely`.

```
python3 build/fetch_sources.py      # Natural Earth 1:10m + terrain tiles into build/cache (~700 MB)
python3 build/build_basemap.py      # data/tiles  (hillshade + water/urban/rail/coast masks, z3–z7)
python3 build/build_history.py      # data/territory.bin + data/meta.json  (~5 min)
python3 build/build_history.py --snap 1941-06-30,1944-08-20   # also write snapshot rasters
python3 build/tools/sheet.py out.png 56 -6 40 32 4 360 300      # contact sheet of the snapshots
python3 build/tests/check_1939.py   # 205 border-town assertions for 1 Sep 1939
node build/tests/determinism.mjs    # play vs jump vs reload give identical state at 40 random instants
```

## How it works

| Layer | What it is |
|---|---|
| `build/build_basemap.py` | Web-Mercator grid (25°W–60°E, 24°N–71.5°N). Hillshade from a terrain DEM. The ink layer holds urban areas, roads, rail and coastline; there is also a water mask and snow. Post-1945 reservoirs (Dnieper and Volga cascades, Tsimlyansk, Kakhovka, Rybinsk …) are removed and Flevoland is restored to water, so the 1939–45 coastlines and rivers are correct. |
| `build/hist/political_1939.py`, `borders.py` | De facto borders on 1 Sep 1939 are rebuilt from modern admin units plus hand-digitised historical lines. These include the German–Polish border, Danzig, Memel, the Vilnius region, the 1920 Finnish border and Petsamo, Petseri and Abrene, the Italian Julian March and Zara, the First Vienna Award, the Protectorate, Zaolzie, Spanish Morocco and Tangier, and the Dodecanese. 205 border towns are checked by tests. |
| `build/hist/units.py` | About 80 political units, each with a faction timeline: Italy 1940→1943, Romania and Bulgaria 1944, Finland, the Vichy colonies, and so on. Colour follows the controller's faction on the displayed date, so a side change recolours without moving territory. |
| `build/hist/campaigns/*.py` | Authored, dated keyframes: front lines, pockets, occupation zones and political changes. Each module lists its sources (official histories, Glantz, Ziemke, Playfair, Ellis, MacDonald and others). |
| `build/hist/compiler.py` | Rasterises every key on a 1.7 km grid and works out, for each cell that changes hands, the time it changes. A geodesic sweep runs from the gaining side's existing territory, so an advance grows outward from the old front. A pocket closes from both sides, and a beachhead grows from the coast. The output is a gzip event stream. |
| `js/territory.js` | Deterministic replay: `stateAt(t)` gives the same answer whether you play, scrub or jump. Each frame uploads a one-day window of "before/after/arrival-time" textures. |
| `js/renderer.js` | WebGL2, drawn in the Miller projection like the reference. A terrain pass draws hillshade and ink. A map pass draws faction colours with a 1-day crossfade, the pale "being taken" band, the white front where warring powers meet, pink national borders and the water hatch. |

**Interpolation vs. documented positions.** The keys are dated positions taken from the sources cited in each module. Between two keys, the compiler moves the front by geodesic distance at a uniform rate, so the state on a date with no key is interpolated, not documented. A transition never spans more than 30 days (`MAX_SPAN`). Long static periods hold their line until the next documented movement. The `src` field on keys and pocket markers records where each position comes from.

## Major changes from the previous version

- **Rendering**
  - Leaflet and vector polygons are replaced by WebGL2 raster compositing over a hillshaded basemap.
  - There are no city labels or political-colour basemap.
  - The palette, front line, pending band, borders and date typography are matched to frames sampled from the reference.
- **Borders**
  - Modern borders are gone. Every border is a de facto line of its date: for example the 1939 Polish corridor, the 1940 Soviet annexations, the Vienna Awards, the partition of Yugoslavia, Alsace-Moselle and Luxembourg annexed, and the restorations of 1944–45.
  - National borders (pink) are separate from control (fill colour) and from the front line (white, drawn only where two powers at war meet).
- **Continuity**
  - Territory is a pure function of time, so there is no flicker or popping and replay is deterministic.
  - Ground that is being taken shows as the lighter band, which advances smoothly from the old front.
- **Coverage**
  - Poland and the 1939 partition.
  - The Winter War.
  - Norway and Denmark.
  - France 1940, including Vichy and the Italian zones.
  - The Soviet annexations.
  - The whole Eastern Front 1941–45, including Finland and the Lapland War.
  - The Balkans, with the partition and the Partisans.
  - Greece and Crete.
  - The Western Desert, Torch and Tunisia.
  - Iraq, Syria-Lebanon and Iran.
  - Sicily and Italy.
  - The Dodecanese.
  - The West from D-Day to the Elbe, with the Atlantic pockets, the Bulge and the Ruhr pocket.
  - The 1945 contact line and the restorations.

## Known gaps and differences (not a 1:1 match)

**Visual**
- **Troop numbers.** As in the reference, each front shows the strength of both sides along the line. The figures come from published totals at dated anchors, listed with sources in `data/strengths.json`: Glantz & House for the Eastern Front, Frieser for France 1940, Playfair, Howe, Fisher and Ellis for the other fronts. They are interpolated linearly day by day, so the exact-looking daily number is an interpolation, not a documented daily count. You can turn them off with the **troops** checkbox.
- **Grid resolution.** The grid cell is about 1.7 km, so at strong zoom front lines show stair-steps. The reference's vector-like edges are smoother at close zoom. At the reference framing the difference is small.
- **Typography.** Captions and the date use system sans-serif fonts. The reference's typeface could not be identified exactly.
- **Colours.** Colours were sampled from compressed video frames. Sampled regions differ from the reference by under about 10 RGB units (Soviet, German, French, British, sea, neutral). The relief in neutral areas is somewhat more contrasty than in the reference.

**Historical data, generalised or missing**
- **Partisan areas** (Yugoslavia, Albania) are shown at the extent of the main liberated territories (Užice 1941, Bihać 1942–43, autumn 1943, mid-1944, the end of 1944). Their real boundaries changed weekly. Partisan areas in Greece, Italy, France (apart from the 1944 FFI liberation of the south-west), Poland and the occupied USSR are not drawn.
- **Behind-the-lines pockets.** Several smaller pockets are absent: the Harz pocket, the German garrisons of the Aegean islands other than Crete, Rhodes and Leros, and the Alpine passes. The Alpine passes are generalised.
- **Africa south of 24°N** (East Africa, French Equatorial Africa, Kufra beyond the grid) is outside the map frame.
- **The desert.** Fronts are drawn only north of about 29°N. Inland the colonial border is kept, apart from Kufra (Free French from 1 Mar 1941) and the Fezzan (Jan 1943).
- **Italy 1943–45.** The Italian Social Republic, OZAK and Alpenvorland are shown as German-held, not as separate states. Former Yugoslav territory annexed by Italy passes to Germany, Croatia or Montenegro on 10 Sep 1943.
- **1945 endpoint.** The Oder–Neisse transfer, the Allied occupation zones of Germany and Austria, and the Trieste Zone A/B split come after the end of the timeline and are not drawn. The map ends on the Soviet–Western contact line of 8–11 May 1945.
- **Daily accuracy.** Days without a documented key are interpolated, as described above. The densest documentation is for the Eastern Front, France 1940, Normandy and the Bulge. North Africa and Italy are keyed every one to three weeks, and more often around major battles.

**Differences found by comparing frames**

I compared reference frames at 8 Nov 1942, 31 Jul 1943, 6 Aug 1944 and 6 Mar 1945 with headless screenshots of this app at the same instants (`build/tools/shot.cjs`). Palette, terrain, white fronts, pending band, pink borders and date layout match closely. The remaining differences are:
- **Brittany, Aug 1944.** The reference shows a narrow Normandy lodgement on 6 Aug 1944. This map shows Brittany overrun, with the Brest, Lorient and St-Nazaire pockets. US armour took Rennes on 4 Aug and reached Brest on 7 Aug, so the documented dates were kept.
- **Yugoslavia, Mar 1945.** The reference shows only Serbia, Montenegro and Macedonia as liberated. This map also shows the Partisan-held parts of Bosnia, Dalmatia and Lika, following the Belgrade Military History Institute maps.
- **Turkey** is kept neutral to the end, as in the reference, even though it declared war on 23 Feb 1945. The declaration was nominal and Turkey took no part in operations.
- **Projection and framing.** The reference uses a **Miller cylindrical** projection, not Web Mercator. Fitted on ten landmarks, its vertical and horizontal scales agree to within 2% under Miller, while Mercator would be off by 16%. The data still live on a Web Mercator grid but are drawn in Miller: the shader converts each pixel to latitude and then to the grid row, and terrain tiles are drawn as warped meshes. After that, an edge-correlation registration against the reference frame peaks at exactly 1.0× scale and a (0, −1) px offset at 1280×720. Local differences of up to about 15 px remain around the British Isles and Ireland, probably because the coastline data differ.
- **Side-by-side images** at five dates are in `docs/compare_*.jpg`, with the reference above and this app below.

**Conflicts between sources, and choices made**
- **Finland** is shown as neutral during the Winter War and as Axis-aligned (a co-belligerent) from 25 Jun 1941 to 19 Sep 1944. The reference colours it this way too, but Finland never joined the Axis.
- **Slovakia** has been an Axis state since 1939, and its Axis status is shown from 1 Sep 1939. This follows the source chronology.
- **The 1939 data in the previous project (`data-world-1939.js`) had errors.** I tested it against the 205 border towns in `build/tests/border_towns.py`, and 55 are on the wrong side or fall outside every polygon. Its borders mix several dates:
  - Danzig is not a Free City. It is part of Germany, while Sopot is in Poland.
  - Memel and Šilutė are shown as Lithuanian, although Germany annexed them in March 1939.
  - Bytom, Zabrze, Racibórz, Syców, Trzcianka and Krzyż are shown as Polish.
  - Tczew, Gniew, Kolno and Grajewo are shown as German.
  - Southern Slovakia and Carpatho-Ukraine (Košice, Komárno, Uzhhorod, Mukachevo, Khust …) are shown as Czechoslovak instead of Hungarian.
  - Zaolzie (Karviná, Bohumín) is shown as German instead of Polish.
  - Finnish Karelia (Vyborg, Sortavala, Kexholm, Suojärvi, Salmi), Petsamo, Petseri, Ivangorod and Abrene are shown as Soviet. These are the 1940–45 borders.
  - Fiume and Postojna are shown as Yugoslav (the post-1947 border). The Dodecanese is shown as Greek.
  - Bender is shown as Soviet, and Tangier as Spanish Morocco.
  - Coastal gaps leave Hel, Cres, Zara and Split outside every polygon.

  All of these are correct in the new base, and all 205 towns pass.
- **The Bulgarian zone in Greece and Macedonia** follows Tomasevich's 1941 partition map. The Bulgarian withdrawal is dated to 20–25 Oct 1944. In some places German rearguards stayed into November, and that is not shown.
- **Crete** is shown as fully German from 1 Jun 1941. After 2 Nov 1944 the German enclave in the west (Chania) is shown as held to 9 May 1945.

## What could not be accessed

- The YouTube URL itself was not downloaded. The uploaded copy of the video (`ww2daybyday.mp4`, 794.7 s) was used instead; frames were extracted from it with ffmpeg.
- `lookwewant.png` was available only as the image attached in the chat. `ww2daybyday.zip` was available and was inspected.
- No source was consulted online. The historical dates and positions come from the published works cited in each campaign module, digitised by hand, so any digitising error is mine and can be fixed in the module concerned.
