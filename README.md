# mise

> *everything in its place*

mise is a voice-first cooking assistant designed for the reality of being in the kitchen — when your hands are covered in flour, you're juggling timers, and the last thing you want to do is touch your phone.

## the problem

cooking apps today expect you to scroll through recipes, tap through steps, and constantly interact with your screen. but when you're actually cooking, your hands are busy. you're chopping, stirring, measuring. you don't want to wash your hands every time you need to check the next step.

## the solution

mise gives you a sous chef in your pocket. just talk to Bruno — tell him what ingredients you have, and he'll suggest what you can make. pick a recipe, and he'll walk you through it step by step, waiting for you to finish each one before moving on. no tapping, no scrolling, no touching your phone with messy hands.

---

## features

### voice-first interaction
the entire experience is designed around conversation. ask Bruno what you can make with chicken and rice. tell him you're done chopping. ask him to repeat that last step. it all just works.

### ingredient-based recipe discovery
don't start with a recipe and go shopping — start with what you have. tell Bruno your ingredients and he'll find recipes that actually work with what's in your kitchen, minimizing what you need to buy.

### step-by-step guidance
Bruno gives you one step at a time and waits for you to finish before moving on. no more accidentally scrolling past where you were or losing your place. just say "done" or "next" when you're ready.

### preference memory
mention that you're vegetarian, allergic to nuts, or hate cilantro — Bruno remembers. next time you cook, he'll automatically filter out recipes that don't work for you. your preferences persist across sessions.

### session continuity
phone died? wifi dropped? no problem. come back and Bruno picks up exactly where you left off. he knows what recipe you were making and what step you were on.

### favorites
loved a recipe? save it to your favorites and make it again anytime. rate your dishes and build your personal cookbook.

### kitchen history
every cooking session is saved. look back at what you've made, when you made it, and how it went.

### shopping lists
planning ahead? tell Bruno what you want to make, check off what you already have, and he'll create a shopping list of what's missing. share it however you like — copy it, text it, or email it to yourself.

---

## use cases

**weeknight cooking**
you're tired, you have random ingredients, and you don't know what to make. tell Bruno what's in your fridge and let him figure it out.

**learning to cook**
bruno explains each step clearly and waits for you to finish. no pressure, no rushing. ask questions if you're confused.

**cooking with kids**
keep your hands free to help little ones while Bruno guides you through the recipe.

**accessibility**
fully voice-controlled for users who have difficulty with touchscreens or prefer audio interfaces.

**meal planning**
check your favorites, see what you've made recently, and decide what to cook based on your history.

**grocery shopping**
start with a recipe instead of ingredients. tell Bruno what you want to make, let him know what you already have, and he'll generate a shopping list of what you're missing. go to the store, come back, and pick up right where you left off — Bruno remembers and starts guiding you through the recipe.

---

## meet bruno

Bruno is your AI sous chef — a friendly raccoon who genuinely loves helping people cook. he's named after the French culinary concept "mise en place" (everything in its place), and he embodies that philosophy: organized, prepared, and ready to help.

he's not a robot reading instructions. he's conversational, encouraging, and adapts to how you cook. he'll give you tips, wait patiently while you prep, and celebrate with you when the dish comes together.

---

## design principles

**hands-free by default**
every interaction can be completed with voice. the UI exists for moments when you want to glance at something, not as the primary interface.

**one thing at a time**
no overwhelming recipe walls. one step, one instruction, one moment at a time.

**remember everything**
preferences, history, favorites, session state — mise remembers so you don't have to.

**meet people where they are**
whether you're a beginner or experienced cook, whether you have a full pantry or three random ingredients, mise adapts.

---

## why it's built this way

**mobile-first, not mobile-friendly**
nobody brings a laptop into the kitchen. mise is a web app, but it's designed for your phone propped up on the counter. the interface is big, simple, and touch-friendly — but you shouldn't need to touch it at all.

**voice as the primary interface**
if the whole point is hands-free cooking, why build around a screen? mise only needs a microphone and a speaker. the visual UI is there for quick glances — seeing Bruno's state, viewing your shopping list — but everything important happens through conversation.

**web, not native**
a web app means no app store friction. open a link and start cooking. it works on any device with a browser and a mic. progressive web apps have come far enough that the experience feels native without the download.

**ai that gets out of the way**
Bruno isn't trying to impress you with how smart he is. he's trying to help you cook dinner. that means short responses, clear instructions, and knowing when to shut up and let you work.

**session persistence as a feature**
real cooking isn't one continuous session. you might plan a recipe, go shopping, come back hours later, get interrupted, continue the next day. mise treats this as normal, not an edge case.

---

## technical decisions

mise was built in one day. that constraint shaped every technical choice — keep the scope small, make sure the core works, ship something usable.

**livekit cloud instead of custom agents**
the "proper" setup would be deepgram for speech-to-text, elevenlabs for voice, a custom agent running in docker on google cloud run, and an mcp server wrapping all the tools. instead, i used livekit cloud with built-in voice pipeline and simple tool definitions. less control, but it works out of the box and let me focus on the product instead of infrastructure.

**pocketbase for everything**
setting up postgres or firebase would have taken hours. pocketbase gives you auth, database, and file storage in a single binary. it runs in docker behind nginx on my home server — no cloud costs, no provisioning, just works. the scale of this project is tiny, so the tradeoff makes sense.

**mailgun for email**
verification emails and password resets go through mailgun. i had plans to use it for more (recipe summaries, shopping lists via email) but ran out of time.

**spoonacular for recipes**
spoonacular has the most detailed recipe data i found — ingredients, steps, equipment, timing, nutritional info. i only scratched the surface of what their api offers. there are more tools i wanted to build but didn't get to.

**home lab hosting**
the backend runs on my home server behind nginx. no cloud bills, no scaling concerns for a project this size. if it ever needed to scale, i'd move it — but for now, this is simpler.

---

## what i'd add with more time

**twilio for telephony**
bruno could text you reminders. set a timer for something in the oven, leave the app, and get a call or text when it's time to check. voice-first should extend beyond the app.

**instacart integration**
after generating a shopping list, one tap to order everything for delivery. the api exists, just didn't have time to wire it up.

**custom voice agent**
more control over the voice pipeline — better latency, custom wake words, finer-tuned responses. livekit cloud is great for prototyping but a custom setup would be more flexible.

**mcp server for tools**
wrapping tools in an mcp server would make it easier to add integrations — smart home devices, calendar, other recipe apis, nutrition tracking.

**more spoonacular tools**
nutritional info, wine pairings, meal planning, ingredient substitutions — the api supports all of this, i just ran out of time to build the tools.

---

## try it

[misekitchen.app](https://misekitchen.app)

---

built by [elian renteria](https://github.com/elianrenteria)
