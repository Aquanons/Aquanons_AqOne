# Aklanon review sheet (plan 70)

Every Aklanon string plan 70 added or changed, for Len to proofread (AKL-08).
Edit the value in `mobile/lib/l10n/app_akl.arb`, then tick the row or write the correction in the last column.
Rows marked **SAFETY CRITICAL** need a second Aklanon reader before the field session.

## Phase 3: screen text (2026-09-26)

| Key | English | Aklanon draft | OK / correction |
|---|---|---|---|
| `advisoriesSubtitle` | Notices from the MDRRMO and your LGU. | Mga abiso halin sa MDRRMO ag sa imong LGU. | |
| `advisoriesLoadFailedTitle` | Could not load advisories | Indi ma-load ro mga abiso | |
| `advisoriesLoadFailedBody` | Check your connection and pull down to try again. | Susiha ro imong koneksyon ag bitada paidaeom agud sulayan liwat. | |
| `advisoriesEmptyTitle` | No active advisories | Waeay aktibo nga abiso | |
| `advisoriesEmptyBody` | Nothing is currently in force for your area. | Waeay abiso nga epektibo subong sa imong lugar. | |
| `advisoriesStaleList` | Showing the last loaded list - refresh failed. | Ginapakita ro huling na-load nga lista - owa nag-refresh. | |
| `chatTitle` | Chat | Istorya | |
| `chatConnected` | Connected to Aquan | Konektado sa Aquan | |
| `chatOnAquanConnecting` | On Aquan - connecting… | Sa Aquan - nagakonekta… | |
| `chatNotOnAquan` | Not on Aquan | Owa sa Aquan | |
| `chatConnecting` | Connecting… | Nagakonekta… | |
| `chatOffline` | Offline | Owa it koneksyon | |
| `chatWaitingForOthers` | Waiting for others… | Nagahueat sa iba… | |
| `chatOnMesh` | On the mesh | Konektado sa network | |
| `chatPeersOnMesh` | {count} on the mesh | {count} ro konektado | |
| `chatWaitingToJoin` | Waiting for others to join… | Nagahueat nga mag-intra ro iba… | |
| `chatEmpty` | No messages yet. Say hi! | Waeay pa it mensahe. Mangumusta! | |
| `enrolInstructions` | Enter the 8-character pairing code provided by the MDRRMO operations desk to link this device to your vessel record. | Isueod ro 8 ka karakter nga pairing code halin sa operations desk it MDRRMO agud ikonekta ro device nga ini sa rekord it imong baroto. | |
| `enrolCodeLabel` | Pairing Code | Code sa pagkonekta | |
| `enrolCodeHint` | e.g. {example} | hal. {example} | |
| `enrolVerifyButton` | Verify Code | Susiha ro Code | |
| `profileOpenSemantics` | Open fisherman profile | Buksi ro profile it mananagat | |
| `emergencyEngine` | Engine failure | Guba ro makina | |
| `emergencyCapsizing` | Capsizing / taking on water | Nagataob / ginasudlan it tubig | |
| `emergencyMedical` | Medical emergency | Medikal nga emerhensya | |
| `emergencyOther` | Other | Iba pa | |
| **SAFETY CRITICAL** `squallReturnNow` | RETURN NOW | ULI EON KAMO | |
| **SAFETY CRITICAL** `squallAlertBody` | A dangerous squall is forecast for your area. | May delikado nga unos nga ginatantiya sa inyong lugar. | |
| **SAFETY CRITICAL** `squallAlertBodyLead` | {minutes, plural, =1{A dangerous squall is forecast to arrive in about 1 minute.} other{A dangerous squall is forecast to arrive in about {minutes} minutes.}} | {minutes, plural, other{May delikado nga unos nga posible nga mag-abot sa mga {minutes} ka minuto.}} | |
| **SAFETY CRITICAL** `squallHeadForShore` | Head for shore. | Magbalik sa baybay. | |
| `squallReportedBy` | Reported by {buoys} | Ginreport it {buoys} | |
| **SAFETY CRITICAL** `squallWatchTitle` | Squall watch | Bantay sa unos | |
| **SAFETY CRITICAL** `squallBannerReturnLead` | {minutes, plural, =1{A squall is forecast to reach your area in about 1 minute. Head back to shore now.} other{A squall is forecast to reach your area in about {minutes} minutes. Head back to shore now.}} | {minutes, plural, other{Posible nga mag-abot ro unos sa inyong lugar sa mga {minutes} ka minuto. Uli eon kamo sa baybay.}} | |
| **SAFETY CRITICAL** `squallBannerReturnSoon` | A squall is forecast to reach your area shortly. Head back to shore now. | Maabot eon ro unos sa inyong lugar. Uli eon kamo sa baybay. | |
| **SAFETY CRITICAL** `squallBannerWatchLead` | {minutes, plural, =1{Unsettled conditions building, possible arrival in about 1 minute. Stay alert.} other{Unsettled conditions building, possible arrival in about {minutes} minutes. Stay alert.}} | {minutes, plural, other{Nagagrabe ro panahon, posible nga mag-abot sa mga {minutes} ka minuto. Mag-andam.}} | |
| **SAFETY CRITICAL** `squallBannerWatchNearby` | Unsettled conditions building nearby. Stay alert. | Nagagrabe ro panahon sa malapit. Mag-andam. | |
| `squallDetectedAt` | Detected at {buoys} | Nakita sa {buoys} | |
| `squallNowcastSynthetic` | AqOne squall nowcast · calibrated on simulated data · not a PAGASA warning | Tantiya it unos it AqOne · gin-calibrate sa simulasyon · indi babala it PAGASA | |
| `squallNowcast` | AqOne squall nowcast · not a PAGASA warning | Tantiya it unos it AqOne · indi babala it PAGASA | |
| `squallAcknowledged` | You acknowledged this warning. It stays until the squall passes. | Nakita mo eon ining babala. Magapabilin ini hangtod makaagi ro unos. | |
| `safetyTitleHighWind` | Wind above threshold | Kusog nga hangin, labaw sa limitasyon | |
| `safetyTitleConditionForecast` | {condition} forecast | Tantiya: {condition} | |
| `safetyTitleCalm` | Conditions look calm | Kalmado ro panahon | |
| `safetyWeatherSummary` | {condition} · {temp}°C · wind {wind} km/h | {condition} · {temp}°C · hangin {wind} km/h | |
| `weatherSourceNote` | Source: Open-Meteo. This is not a PAGASA warning. Always follow the official sea condition and advisories. | Halin sa Open-Meteo. Indi ini babala it PAGASA. Pirmi nga sunda ro opisyal nga kahimtangan it dagat ag mga abiso. | |
| `weatherSourceNoteThreshold` | Source: Open-Meteo · threshold {kph} km/h. This is not a PAGASA warning. Always follow the official sea condition and advisories. | Halin sa Open-Meteo · limitasyon {kph} km/h. Indi ini babala it PAGASA. Pirmi nga sunda ro opisyal nga kahimtangan it dagat ag mga abiso. | |
| `weatherHighWindNote` | Wind {wind} km/h - above the {kph} km/h threshold. | Hangin {wind} km/h - labaw sa {kph} km/h nga limitasyon. | |
| `weatherAdverseNote` | {condition} forecast - adverse condition. | Tantiya: {condition} - indi maayad nga panahon. | |
| `weatherWindLine` | Wind {wind} km/h · {location} | Hangin {wind} km/h · {location} | |
| `forecastLongRangeSemantics` | Longer-range outlook, lower confidence. | Maeayo nga tantiya, mas ubos nga kasiguruhan. | |
| `loadingShort` | Loading… | Nagasueod… | |
| `advisoryAppNotice` | APP NOTICE | PAHIBALO IT APP | |
| `advisoryAppNoticeBody` | A message from the app developers. This is not an official MDRRMO or LGU advisory. | Mensahe halin sa mga naghimo it app. Indi ini opisyal nga abiso it MDRRMO ukon LGU. | |
| `advisoryInForceUntil` | In force until {date} | Epektibo hangtod {date} | |
| `advisoryViewAllMore` | View all ({count} more) | Tan-awa ro tanan ({count} pa) | |
| `advisoryViewAll` | View all advisories | Tan-awa ro tanan nga abiso | |
| `advisoryPhotoOffline` | Photo unavailable offline | Waeay litrato kon offline | |
| `buoyNoneTitle` | No buoy connected | Waeay konektado nga buoy | |
| `buoyNoneBody` | Join a buoy WiFi network to hand off an SOS. | Magkonekta sa WiFi it buoy agud mapasa ro SOS. | |
| `buoyTitle` | Buoy {id} | Buoy {id} | |
| `buoyUplinkUp` | Link to shore is up. Your SOS will reach the rescue centre now. | Konektado sa baybay. Madangat eon ro imong SOS sa rescue center. | |
| `buoyUplinkDown` | Link to shore is down. This buoy will hold your SOS and deliver it automatically once the link returns. | Owa it koneksyon sa baybay. Ining buoy ro magatipig it imong SOS ag awtomatiko nga igapadaea kon magbalik ro koneksyon. | |
| `buoyQueued` | {count, plural, =1{1 message waiting on this buoy} other{{count} messages waiting on this buoy}} | {count, plural, other{{count} ka mensahe nga nagahueat sa ining buoy}} | |
| `offlineMapShowing` | Showing saved map data · {age} | Ginapakita ro na-save nga mapa · {age} | |
| **SAFETY CRITICAL** `offlineMapHazardsMissing` | Hazard warnings are NOT included - they expire after 6 hours. Assume nothing about current conditions. | OWA kaupod ro mga babala sa peligro - nagapaso sanda matapos ro 6 ka oras. Indi magsalig sa kahimtangan subong. | |
| `offlineMapStale` | Buoys and warnings are from the last time you had signal, not from now. | Ro mga buoy ag babala halin sa huling oras nga may signal ka, indi subong. | |
| `seaConditionChecking` | Checking sea condition… | Ginasusi ro kahimtangan it dagat… | |
| **SAFETY CRITICAL** `seaConditionUnavailable` | Sea condition unavailable. Check advisories before heading out. | Waeay datos sa kahimtangan it dagat. Basaha ro mga abiso bag-o magguwa. | |
| `seaConditionBuoyCheck` | Buoy check: {speed} m/s current | Susi it buoy: {speed} m/s nga sueog | |
| `seaConditionSetBy` | Set by {name} | Ginbutang ni {name} | |
| `ageJustNow` | just now | subong eang | |
| `ageMinutes` | {minutes} min | {minutes} ka minuto | |
| `ageHours` | {hours}h | {hours} ka oras | |
| `ageDays` | {days}d | {days} ka adlaw | |
| `ageAgo` | {age} ago | {age} ro nagtaliwan | |
| `infoAboutBody` | AqOne<br>Gabay sa Bawat Alon, Konektado sa Bawat Layon<br><br>Fishermen in New Washington, Aklan lose mobile signal as soon as they reach the fishing ground. When something goes wrong out there, there is no way to call for help, and the MDRRMO usually hears about it hours later by word of mouth.<br><br>AqOne carries a distress message over a radio mesh instead of the cellular network. Your phone hands the SOS to the nearest anchored buoy over its WiFi. Buoys pass it along by LoRa radio until one of them reaches shore and forwards it to the MDRRMO dashboard.<br><br>Your phone never needs a signal. | AqOne<br>Gabay sa Bawat Alon, Konektado sa Bawat Layon<br><br>Ro mga mananagat sa New Washington, Aklan hay nawad-an it signal it cellphone pag-abot sa pangisdaan. Kon may matabo nga indi maayad didto, waeay paagi nga makapangayo it bulig, ag kasagaran oras pa ro maglabay bag-o mahibaeuan it MDRRMO halin sa istorya it iba.<br><br>Ginadaea it AqOne ro mensahe it peligro paagi sa radyo nga network imbes sa cellular. Ginatugyan it imong telepono ro SOS sa pinakamalapit nga buoy paagi sa WiFi. Ginapasa it mga buoy paagi sa LoRa nga radyo hangtod maabot it sangka buoy ro baybay ag ipadaea sa dashboard it MDRRMO.<br><br>Indi kinahangean it imong telepono it signal. | |
| `infoHelpBody` | Sending an SOS<br><br>1. Connect your phone to the WiFi of the nearest AqOne buoy. The network name starts with "AqOne-".<br>2. Open this app and press the red SOS button.<br>3. Watch the status on the message. It tells you exactly how far your SOS has travelled.<br><br>What the four statuses mean<br><br>Saved - the SOS is on your phone only. No buoy is in range yet. The app keeps trying on its own.<br><br>Relayed - a buoy has taken your SOS and is passing it along the radio mesh. This is as much as your phone can know without a signal.<br><br>Delivered - the MDRRMO dashboard has received it.<br><br>Acknowledged - a responder has seen it and is acting on it.<br><br>The app will never show a later status than the one it has actually observed. If your message is stuck at Relayed, it is genuinely still waiting on the mesh.<br><br>If no buoy is in range<br><br>Your SOS is not lost. It stays on your phone and is sent automatically as soon as a buoy is reachable, even if you close the app. | Pagpadaea it SOS<br><br>1. Ikonekta ro imong telepono sa WiFi it pinakamalapit nga AqOne buoy. Ro ngaran it network hay nagasugod sa "AqOne-".<br>2. Buksi ining app ag pinduta ro puea nga SOS nga button.<br>3. Tan-awa ro status sa mensahe. Ginasugid ini kon hasta diin eon nakaabot ro imong SOS.<br><br>Kahueogan it apat nga status<br><br>Nasave - ro SOS hay sa imong telepono pa eang. Waeay pa it buoy nga malapit. Padayon nga magatinguha ro app.<br><br>Napasa - may buoy eon nga nagbaton it imong SOS ag ginapasa sa radyo nga network. Amo ra eang ro mahibaeuan it imong telepono kon waeay signal.<br><br>Nadangat - nabaton eon it dashboard it MDRRMO.<br><br>Nasabat - nakita eon it responder ag ginaaksyunan eon.<br><br>Indi gid magpakita ro app it status nga owa pa gid natabo. Kon nagauntat ro imong mensahe sa Napasa, matuod nga nagahueat pa ini sa network.<br><br>Kon waeay buoy nga malapit<br><br>Owa madura ro imong SOS. Magapabilin ini sa imong telepono ag awtomatiko nga igapadaea kon may maabot eon nga buoy, maskin isara mo ro app. | |
| `infoPrivacyBody` | What AqOne collects<br><br>This app does not ask for an account, a password, an email address, or a phone number. There is no user database.<br><br>When you first open the app it creates a random identifier on your device and stores it locally. That identifier, together with the boat name you enter, is what a responder sees next to your distress call.<br><br>When you send an SOS, the app transmits:<br><br>• your boat name<br>• your GPS position, if your phone has a fix at that moment<br>• the short note you typed, if you typed one<br>• the time you pressed the button<br><br>Precise position is only sent as part of an SOS you deliberately send. The app does not track or transmit your location in the background, and it does not record where you fish.<br><br>Weather forecasts and maps<br><br>Weather forecasts use your approximate location (about 11 km) to retrieve conditions for your general area without disclosing your exact coordinates. When viewing the online map, the app fetches map tiles for the area you are viewing directly from OpenStreetMap.<br><br>How it travels<br><br>An SOS is relayed by radio between buoys. Messages are signed so a responder can tell a real buoy from a fake one, but the content itself is not encrypted end to end in this version. Treat an SOS as a public radio call, because that is what it is.<br><br>Deleting your data<br><br>Uninstalling the app removes the identifier and every message stored on your phone. Distress calls already delivered to the MDRRMO remain part of their incident record. | Ano ro ginakuha it AqOne<br><br>Indi mangayo ining app it account, password, email, ukon numero it telepono. Waeay user database.<br><br>Pag-abri mo it app sa una nga beses, maghimo ini it random nga identifier sa imong device ag ginatipig diya eang. Ro identifier nga ina, kaupod ro ngaran it baroto nga imong ginsueod, ro makita it responder tupad sa imong tawag it bulig.<br><br>Kon magpadaea ka it SOS, ginapadaea it app:<br><br>• ro ngaran it imong baroto<br>• ro imong GPS nga posisyon, kon may GPS ro imong telepono sa ruyon nga oras<br>• ro maikli nga nota nga imong ginsulat, kon may ginsulat ka<br>• ro oras nga imong ginpindot ro button<br><br>Ro eksakto nga posisyon hay ginapadaea eang kaupod it SOS nga hungod mo nga ginpadaea. Indi ginasunod ukon ginapadaea it app ro imong lokasyon sa background, ag indi ginarekord kon diin ka nagapangisda.<br><br>Tantiya it panahon ag mapa<br><br>Ro tantiya it panahon hay nagagamit it tantiya nga lokasyon (mga 11 km) agud makuha ro kahimtangan sa imong lugar nga indi ginasugid ro eksakto mong posisyon. Kon ginatan-aw ro online nga mapa, ginakuha it app ro mga tile it mapa para sa lugar nga imong ginatan-aw direkta halin sa OpenStreetMap.<br><br>Paano ini nagabiyahe<br><br>Ro SOS hay ginapasa paagi sa radyo halin sa sangka buoy pakadto sa iba. Ro mga mensahe hay may pirma agud mahibaeuan it responder kon matuod nga buoy ukon peke, pero ro sueod mismo hay owa naka-encrypt end to end sa ining bersyon. Isipa ro SOS bilang publiko nga tawag sa radyo, tungod amo ra gid ina.<br><br>Pagpanas it imong datos<br><br>Kon i-uninstall ro app, madura ro identifier ag ro tanan nga mensahe nga natipig sa imong telepono. Ro mga tawag it bulig nga nadangat eon sa MDRRMO hay magapabilin nga parte it rekord it insidente it MDRRMO. | |
| **SAFETY CRITICAL** `infoTermsBody` | Please read this before relying on AqOne.<br><br>AqOne is a prototype<br><br>This software was built for a hackathon and has not been certified, independently tested, or approved as marine safety equipment.<br><br>It is not a replacement for safety gear<br><br>Do not go to sea relying on this app alone. Carry the flotation, signalling and communication equipment you would normally carry. AqOne is an addition to those, never a substitute.<br><br>Delivery is not guaranteed<br><br>An SOS travels by radio between buoys. Radio is affected by weather, distance, obstructions, buoy battery level, and interference. A message may be delayed or may not arrive at all. The app shows you honestly how far your message has reached, and never claims more than it knows.<br><br>Coverage is limited<br><br>AqOne only works within radio range of a deployed buoy. Outside that range your SOS stays saved on your phone until you come back into range.<br><br>Responsible use<br><br>Send an SOS only in a genuine emergency. False alarms waste rescue resources and put responders at risk. | Palihog basaha ini bag-o magsalig sa AqOne.<br><br>Prototype pa eang ro AqOne<br><br>Ining software hay ginhimo para sa hackathon ag owa pa na-certify, owa pa nasusi it iba, ag owa pa naaprobahan bilang gamit pangkaluwasan sa dagat.<br><br>Indi ini kapuli it gamit pangkaluwasan<br><br>Indi magdagat nga ining app eang ro ginasaligan. Dae-a ro salbabida, gamit pang-signal ag komunikasyon nga pirmi mo nga ginadaea. Dugang eang ro AqOne sa ruyon, indi gid kapuli.<br><br>Indi siguro ro pagdangat<br><br>Ro SOS hay nagabiyahe paagi sa radyo halin sa sangka buoy pakadto sa iba. Ro radyo hay naapektuhan it panahon, kalayuon, mga nagaharang, baterya it buoy, ag interference. Ro mensahe hay mahimo nga maulang ukon indi gid makaabot. Matuod nga ginapakita it app kon hasta diin eon nakaabot ro imong mensahe, ag indi gid magsugid it labaw sa ana nga nahibaeuan.<br><br>Limitado ro sakop<br><br>Nagagana eang ro AqOne sa sulod it sakop it radyo it sangka buoy. Sa guwa it ruyon nga sakop, magapabilin nga naka-save ro imong SOS sa imong telepono hangtod makabalik ka sa sakop.<br><br>Responsable nga paggamit<br><br>Magpadaea eang it SOS kon matuod nga emerhensya. Ro sala nga alarma hay nagausik it gamit sa pagsagip ag ginabutang sa peligro ro mga responder. | |

Existing keys whose Aklanon value was still English:

| Key | English | Aklanon draft | OK / correction |
|---|---|---|---|
| `navHome` | Home | Umpisa | |
| `navProfile` | Profile | Akon | |
| `profileTitle` | Profile | Akon nga Profile | |
| `deliveryMetaResponder` | Responder | Tigsagip | |
| `wifiTitle` | Buoy Wi-Fi | Wi-Fi it Buoy | |
| `weatherLocationDefault` | Aklan (default) | Aklan (kinaandan) | |

## Phase 3: Tagalog and Cebuano words in earlier drafts

| Key | English | Aklanon draft | OK / correction |
|---|---|---|---|

Earlier drafts that used Tagalog or Cebuano function words (ang, kung, ug, kaysa), rewritten with ro, kon, it:

| Key | English | Aklanon draft | OK / correction |
|---|---|---|---|
| `squallStaleBodyWithAge` | Last known reading {age} ago. Not showing a squall status right now. | Huling nahibaeuan nga reading: {age} ro nagtaliwan. Waeay ipakita nga kahimtangan it unos subong. | |
| `squallWarningStays` | The warning stays on your screen until the squall passes. | Magapabilin ro babala sa imong screen hangtod makaagi ro unos. | |
| `chatWithBoatsTooltip` | Chat with nearby boats | Makig-istorya sa mga baroto nga malapit | |
| `sosDescribeWrong` | Describe what is wrong | Isugid kon ano ro problema | |
| `etaArrivalOverdue` | ARRIVAL OVERDUE | NAULANG RO PAG-ABOT | |
| `stayWithBoat` | Stay with your boat if it is still afloat. It is easier to spot than a person in the water. | Pabilin sa imong sakayan kon nagalutaw pa. Mas masayon ini makita kay sa tawo sa tubig. | |
| `chatHint` | Type a message… | Magsulat it mensahe… | |
| `sosClosedUnconfirmed` | MDRRMO closed this call without reaching you. If you still need help, press SOS again. | Ginsarado it MDRRMO ro tawag nga raya nga uwa ka naabtan. Kon kinahangean mo pa it bulig, pinduton liwat ro SOS. | |
| `sosStandDownConfirmBody` | Rescue will be called off. Only do this if everyone is safe. | Kakanselahon ro pagsagip. Obrahon eang raya kon eowas eon ro tanan. | |
