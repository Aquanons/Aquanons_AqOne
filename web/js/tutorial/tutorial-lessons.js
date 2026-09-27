// The dashboard tutorial's lessons (docs/72_DASHBOARD_DEMO_MODE_IMPLEMENTATION_PLAN.md).
//
// Each lesson stands alone: it opens on its own recording
// (web/data/tutorial/<id>.json, made by tools/render-check/record_tutorial.mjs),
// so a learner can start at any lesson and skip any step. Read by the profile
// page's "Learn AqOne" tab and by the dashboard coach.
//
// A step may name a `target` to highlight, `before` actions that open what it
// talks about, a `cue` that moves the recording on (an SOS arriving), and a
// `waitFor` pattern: the step continues on its own once the learner does the
// action whose recorded phase label matches it.
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && typeof module.exports === 'object') {
    module.exports = factory();
  } else {
    root.AqOneTutorialLessons = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var openAlertDrawer = [{ tab: 'alerts' }, { click: '#alert-list .alert-row', unless: '#sos-drawer.open' }];

  return [
    {
      id: 'console',
      title: 'Find your way around',
      summary: 'The map, the buoy network and the figures that tell you if anything needs you.',
      minutes: 3,
      steps: [
        {
          title: 'Welcome to the AqOne tutorial',
          body: 'This console is filled with a practice scenario recorded from the real system. Nothing here is live, and nothing you press is sent to anyone. Use Next and Back, skip any step, or pick another lesson from Lessons at the top.'
        },
        {
          target: '#live-alert-banner',
          title: 'Three figures to watch',
          body: 'Open distress calls, squall RETURN NOW detections, and how long ago the SOS feed last refreshed. On a real shift the last card turns amber, then red, if the feed stops arriving.'
        },
        {
          target: '#map',
          before: [{ click: '#compass-widget' }, { click: '#toggle-buoys', unless: '#toggle-buoys:checked' }],
          title: 'Your service area',
          body: 'The dashed green outline is New Washington\'s municipal waters. Purple pins are buoys and blue pins are shore gateways. Distress calls, drift areas and danger zones are drawn here too.'
        },
        {
          target: '#panel-buoys',
          before: [{ click: '#rail-btn-buoy', unless: '#rail-btn-buoy.active' }],
          title: 'The buoy network',
          body: 'Every registered buoy, when the backend last heard it, and whether it links straight to a shore gateway. A fisher\'s phone hands its SOS to the nearest buoy over WiFi; buoys relay it over LoRa to shore.'
        },
        {
          target: '#panel-layers',
          before: [{ click: '#rail-btn-layers', unless: '#rail-btn-layers.active' }],
          title: 'Map layers',
          body: 'Turn on Buoy Coverage Zones to see where a phone can reach a buoy, and Mesh Network to see the LoRa links that carry an SOS to shore.'
        },
        {
          target: '#stats-widget',
          title: 'Live Overview and the tabs',
          body: 'Measured figures for the network, then one tab each for vessels, alerts, evaluation metrics and trip checks. The other lessons walk through them one at a time.'
        }
      ]
    },
    {
      id: 'squall',
      title: 'Read a squall nowcast',
      summary: 'How falling pressure across the buoys becomes a squall warning.',
      minutes: 2,
      steps: [
        {
          target: '#squall-card',
          title: 'Squall nowcasting',
          body: 'The model watches air pressure at every buoy. A drop that travels from buoy to buoy is a squall front moving across the water, and the card shows how far along it is.'
        },
        {
          target: '#squall-body',
          title: 'The pressure traces',
          body: 'Each line is one buoy the front has reached, in the order it reached them. The time between their drops is how the model estimates the front\'s speed and direction.'
        },
        {
          target: '.danger-zone-status',
          title: 'Near-shore danger scan',
          body: 'A separate, experimental model scores near-shore waters from wind and wave forecasts. It is advisory and never replaces a responder\'s judgement.'
        },
        {
          target: '#live-alert-banner .metric-card:nth-child(2)',
          title: 'When to call boats back',
          body: 'This card turns to RETURN NOW only when the squall model reaches its return level. The next lesson picks up from there.'
        }
      ]
    },
    {
      id: 'warn',
      title: 'Warn the fleet',
      summary: 'A RETURN NOW squall, the advisory, and the sea condition fishers see on their phones.',
      minutes: 2,
      steps: [
        {
          target: '#live-alert-banner .metric-card:nth-child(2)',
          title: 'RETURN NOW',
          body: 'The squall front has reached the return level. Boats still out need to head for shore.'
        },
        {
          target: '#panel-advisories',
          before: [{ click: '#rail-btn-advisories', unless: '#rail-btn-advisories.active' }],
          title: 'The advisory',
          body: 'A RETURN NOW advisory was published for every municipality. Advisories reach phones the next time they sync.'
        },
        {
          target: '#sea-condition-card',
          before: [{ click: '#advisory-panel-close', unless: '#panel-advisories:not(.active)' }],
          title: 'Declare the sea condition',
          body: 'Choose Not Advised, add a short reason, and press Set Status. Fishers see it on the app\'s home screen with your name and the time.',
          waitFor: '/api/sea-condition$'
        },
        {
          target: '#sea-condition-current',
          title: 'Declared',
          body: 'The card now shows the status you set, who set it and when. It stays until someone changes it.'
        }
      ]
    },
    {
      id: 'trip-checks',
      title: 'Follow up an overdue boat',
      summary: 'The vessel risk feed and the trip check a late boat becomes.',
      minutes: 3,
      steps: [
        {
          target: '#tab-vessels',
          before: [{ tab: 'vessels' }],
          title: 'Vessel risk feed',
          body: 'The trip profile model learns each boat\'s usual trips and flags one that is late against its own habits, not a fixed curfew.'
        },
        {
          target: '#trip-checks-list',
          before: [{ tab: 'tripchecks' }],
          title: 'A trip check',
          body: 'A boat late beyond its expected-contact window becomes a case for a person to review. The largest reason is written on the case.'
        },
        {
          target: '#trip-checks-list [data-case-action="acknowledge"]',
          before: [{ tab: 'tripchecks' }],
          title: 'Take the case',
          body: 'Press Acknowledge so the rest of the team knows someone is on it.',
          waitFor: '/acknowledge$'
        },
        {
          target: '#trip-checks-list [data-case-action="escalate"]',
          title: 'Escalate',
          body: 'If calls and nearby boats cannot reach the crew, press Escalate and give a short reason. An escalated case can open a drift prediction.',
          waitFor: '/escalate$'
        },
        {
          target: '#trip-checks-list [data-case-action="activity"]',
          title: 'Every action is recorded',
          body: 'View Activity shows who acknowledged and escalated the case, and when.'
        }
      ]
    },
    {
      id: 'sos',
      title: 'Receive and acknowledge an SOS',
      summary: 'An SOS arrives; you acknowledge it and send an ETA back to the fisher.',
      minutes: 3,
      steps: [
        {
          target: '#live-alert-banner',
          title: 'An SOS is on its way',
          body: 'A fisher has pressed SOS. Watch the top card and the map: the call arrives in a few seconds.',
          cue: 'sos-arrives'
        },
        {
          target: '#live-alert-banner .metric-card:first-child',
          title: 'It arrived',
          body: 'The open SOS count went up. With the alarm sound on, the console also rings until every call is acknowledged.'
        },
        {
          target: '.live-sos-marker',
          title: 'Where it came from',
          body: 'The SOS marker sits at the position the phone sent. Click it any time to open the call.'
        },
        {
          target: '#alert-list',
          before: [{ tab: 'alerts' }],
          title: 'The Alerts tab',
          body: 'Open calls, newest first, with how each one reached shore: through the LoRa mesh via a buoy, or directly over the internet.'
        },
        {
          target: '#sos-drawer',
          before: openAlertDrawer,
          title: 'The call',
          body: 'Who sent it, where, when it was pressed, and the path it took. A DEMO badge marks practice data like this.'
        },
        {
          target: '#sos-btn-acknowledge',
          before: openAlertDrawer,
          title: 'Acknowledge',
          body: 'Press Acknowledge, choose a status, an ETA and a short note, then send. They go back to the fisher\'s phone, which shows Acknowledged.',
          waitFor: '/acknowledge$'
        },
        {
          target: '#sos-drawer',
          title: 'Acknowledged',
          body: 'The drawer now shows your status and a live countdown to your ETA. The app only ever shows a state it has evidence for: saved, relayed, delivered, acknowledged.'
        }
      ]
    },
    {
      id: 'drift',
      title: 'Predict drift and plan the search',
      summary: 'Open a drift case, read the search areas, report a searched area and rerun.',
      minutes: 4,
      steps: [
        {
          target: '#sos-btn-open-drift',
          before: openAlertDrawer,
          title: 'Open a drift case',
          body: 'From an acknowledged SOS, press Open drift case, choose what is in the water, and open it.',
          waitFor: 'POST /api/ai/drift/cases$'
        },
        {
          target: '#drift-card',
          before: [{ click: '#sos-drawer-close', unless: '#sos-drawer:not(.open)' }],
          title: 'The drift prediction',
          body: 'The model follows two thousand possible paths using observed currents and wind. It is a probability, not a location guarantee.'
        },
        {
          target: '#ai-map-key',
          title: 'Search areas on the map',
          body: 'The rings hold 50, 75 and 95 percent of the likely positions. Search the smallest ring first.'
        },
        {
          target: '#ai-drift-search',
          title: 'Report a searched area',
          body: 'Press Mark a searched area, click two corners on the map, and submit. The model lowers the chance there and recommends the next area. The tutorial then shows the area it recorded earlier.',
          waitFor: '/searched$'
        },
        {
          target: '#ai-drift-search',
          title: 'Rerun with fresh data',
          body: 'Press Rerun drift to compute a new run from the latest currents. Earlier runs stay in the case history.',
          waitFor: '/rerun$'
        },
        {
          target: '#drift-card',
          title: 'Advice, not orders',
          body: 'Drift and search advice support the responder. The manual SOS path works even when every model is unavailable.'
        }
      ]
    },
    {
      id: 'close-out',
      title: 'Close the case',
      summary: 'Resolve the call with a reason, then see how the models are measured.',
      minutes: 2,
      steps: [
        {
          target: '#sos-btn-resolve',
          before: openAlertDrawer,
          title: 'Resolve',
          body: 'When the crew is safe, press Resolve Incident and pick what happened. A resolved call can be reopened if it was closed by mistake.',
          waitFor: '/resolve$'
        },
        {
          target: '#resolved-feed-list',
          title: 'Resolved calls',
          body: 'Closed calls move here with how they ended, so the next shift can see what happened.'
        },
        {
          target: '#tab-sar',
          before: [{ tab: 'sar' }],
          title: 'How the models are measured',
          body: 'These figures come from the evaluation scripts, not from live operations. The lead time and false alarm rate decide whether a model is worth trusting.'
        },
        {
          title: 'You finished the tutorial',
          body: 'Pick any lesson again from Lessons, or press Exit tutorial to return to the live console.'
        }
      ]
    }
  ];
});
