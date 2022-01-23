from logging import lastResort
from botocore.utils import S3EndpointSetter
from boto3.dynamodb.conditions import Key, Attr
import discord
from discord.ext import commands, tasks
from discord.ext.commands import CommandNotFound
from discord.utils import get
import gspread
from oauth2client.service_account import ServiceAccountCredentials, _JWTAccessCredentials
from datetime import date
import datetime
import boto3
import re
from dotenv import load_dotenv
from pathlib import Path
import os
import difflib

from PersonalBest import PersonalBest
from PersonalBestStatus import PersonalBestStatus

env_path = Path('.')/'.env'
load_dotenv(dotenv_path=env_path)

# Setup Google Sheets connection
scope = ['https://spreadsheets.google.com/feeds',
'https://www.googleapis.com/auth/drive']
sheets_creds = ServiceAccountCredentials.from_json_keyfile_name('credentials/sheets/client_secret.json', scope)
sheets_client = gspread.authorize(sheets_creds)
ranks_spreadsheet = sheets_client.open(os.getenv("SHEETS_RANKS_SPREADSHEET"))
pointsSheet = ranks_spreadsheet.worksheet(os.getenv("SHEETS_POINTS_SHEET"))
infoSheet = ranks_spreadsheet.worksheet(os.getenv("SHEETS_INFO_SHEET"))
diary_hiscores_spreadsheet = sheets_client.open(os.getenv("SHEETS_HISCORES_SPREADSHEET"))
pbLogSheet = diary_hiscores_spreadsheet.worksheet(os.getenv("SHEETS_PBLOG_SHEET"))

# Setup Discord connection
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=os.getenv("DISCORD_PREFIX"), case_insensitive=True, intents=intents)

# discord vars
BOT_UID = int(os.getenv("DISCORD_BOT_UID"))
DEV_UID = int(os.getenv("DISCORD_DEV_UID"))

#sanity disc
PB_LEADERBOARD_ID = int(os.getenv("SERVER_PB_LEADERBOARD_ID"))
PB_SUBMISSIONS_ID = int(os.getenv("SERVER_PB_SUBMISSIONS_ID"))
PENDING_PBS_ID = int(os.getenv("SERVER_PENDING_PBS_ID"))
PENDING_APPLICATIONS_ID = int(os.getenv("SERVER_PENDING_APPLICATIONS_ID"))
TRIAL_APPLICATIONS_CATEGORY_ID = int(os.getenv("SERVER_TRIAL_APPLICATIONS_CATEGORY_ID"))
TRIAL_MEMBER_ROLE_ID = int(os.getenv("SERVER_TRIAL_MEMBER_ROLE_ID"))
MEMBERS_CHAT_ID = int(os.getenv("SERVER_MEMBERS_CHAT_ID"))
SERVER_ID = int(os.getenv("SERVER_SERVER_ID"))
OFFICIAL_ROLE_ID = int(os.getenv("SERVER_OFFICIAL_ROLE_ID"))
MEMBERS_ROLES = os.getenv("SERVER_MEMBERS_ROLES")

# Setup Database Connection
boto3_client = boto3.client('dynamodb',aws_access_key_id=os.getenv("AWS_ACCESS"), aws_secret_access_key=os.getenv("AWS_SECRET"), region_name=os.getenv("AWS_REGION"))
boto3_resource = boto3.resource('dynamodb',aws_access_key_id=os.getenv("AWS_ACCESS"), aws_secret_access_key=os.getenv("AWS_SECRET"), region_name=os.getenv("AWS_REGION"))

# Array of Message objects of applications posted in pending-applications channel
pendingApps = []
# Array of Member objects who have a pending application posted, same index as their Message in pendingApps
pendingUsers = []
# List of Member objects who have app DMs to keep checking
openDms = []
# List of DateTime objects containing the time that open DMs need to be closed, these are checked every 15 seconds for expiry
dmCloseTimes = []

# List of PersonalBest objects who have an open pb submission
pendingPBs = []
# List containing the downloaded database for local use
pbDatabase = []
# List containing top 3 times of each pb, in order that they are displayed in pb channel
top3Pbs = []

# List of PB Bosses
pbBosses = ["Chambers of Xeric (Challenge mode)", "Chambers of Xeric", "Theatre of Blood", "6 Jads", "Fight Caves", "Corrupted Gauntlet", "The Inferno"]
# List of Abbreviations for PB Bosses that auto predictor could miss
bossAbbreviations = {
  "tob": "Theatre of Blood",
  "cox": "Chambers of Xeric",
  "cm": "Chambers of Xeric (Challenge mode)",
  "cg": "Corrupted Gauntlet"
}

appsOpen = [False]
pbsRequireUpdate = [False]
pbSubmittedUpdate = [False]
lastRefresh = [datetime.datetime.now()]

@bot.event
async def on_ready():
    get_db()
    #populate top3pbs with false data to prevent null pointers
    for i in range(12):
        pbs = [0,0,0]
        top3Pbs.append(pbs)
    
    await update_pbs()

    checkStoredDateTimes.start()
    recheckPbs.start()
    checkPbSubmissions.start()
    
@tasks.loop(seconds=300.0)
async def recheckPbs():
    now = datetime.datetime.now()
    if lastRefresh[0] < now:
        if pbsRequireUpdate[0]:
            await update_pbs()

@tasks.loop(seconds=60.0)
async def checkPbSubmissions():
    if pbSubmittedUpdate[0] == True:
        pbSubmittedUpdate[0] = False
        await update_pbs()
        

@tasks.loop(seconds=30.0)
async def checkStoredDateTimes():
    now = datetime.datetime.now()
    for dateTime in dmCloseTimes:
        if dateTime < now:
            member = openDms[dmCloseTimes.index(dateTime)]
            direct_message = await member.create_dm()
            await direct_message.send("Application timed out. Please type !apply in #public if you wish to apply again.")
            openDms.remove(openDms[dmCloseTimes.index(dateTime)])
            dmCloseTimes.remove(dateTime)

    for pb in pendingPBs:
        if pb.getTimeoutTime() < now  and pb.getStatus() == PersonalBestStatus.CREATING:
            guild = get(bot.guilds, id = SERVER_ID)
            pb_submissions = get(guild.channels, id = PB_SUBMISSIONS_ID)
            member = pb.getSubmitter()
            await pb_submissions.send(member.mention + " Submission timed out. Please start a new submission.")
            pendingPBs.remove(pb)


@bot.command(name='closeapps')
@commands.has_role(OFFICIAL_ROLE_ID)
async def event(ctx):
    appsOpen[0] = False
    await ctx.send("Apps closed.")
    
@bot.command(name='openapps')
@commands.has_role(OFFICIAL_ROLE_ID)
async def event(ctx):
    appsOpen[0] = True
    await ctx.send("Apps opened.")

@bot.command(name='refreshpbs')
@commands.has_role(OFFICIAL_ROLE_ID)
async def event(ctx):
    top3Pbs.clear()
    for i in range(13):
        pbs = [0,0,0]
        top3Pbs.append(pbs)
    await update_pbs()
    await ctx.send("Force refresh complete.")


#apply
@bot.command(name='apply')
async def event(ctx):
    if appsOpen[0]:
            emptyApp = "Thank you for applying to Sanity! Please copy and paste this application completed into a SINGLE reply here! You have 30 minutes to complete this, otherwise you will have to type !apply again in #public \n\n```Main RSN: \nAlt RSN (if applicable, 1 max): \nPast RSNs [Name as many as you can remember]: \nPreferred Name (This name will be your name on Discord and will not change): \nPlease list who can vouch for you in Sanity: \nHow did you find out about Sanity?: \nTell us about yourself: \nPrevious clans and why you left: \nTimezone: \nPicture of stats [Gyazo or Imgur ONLY] (Must have 78 Herblore, 82+ Construction, 99 ALL combat skills, 90 prayer, and 1750 Total)  [No cropped images]: \nPicture of required items [Gyazo or Imgur ONLY] [SEE REQUIREMENT GRAPHIC]: \nPicture of Boss Log [Gyazo or Imgur ONLY] [Must include 50+ TOB and 100+ COX KC]: \nPicture of Prayer Book [Gyazo or Imgur ONLY] [Must include Rigour and Augury]: \nPicture of your TempleOSRS page [300+ EHB] \nHave you read the rules?: \nWould you like to add anything?: ```"
            member = ctx.author
            channel = await member.create_dm()
            await channel.send(emptyApp)
            openDms.append(member)
            now = datetime.datetime.now()
            now_plus_30 = now + datetime.timedelta(minutes = 30)
            dmCloseTimes.append(now_plus_30)
    else:
        await ctx.channel.send("https://imgur.com/a/mGgieUB")
#pb
@bot.command(name='pb')
async def event(ctx):
    member = ctx.author
    found = False
    if (member.id != BOT_UID and ctx.channel.id == PB_SUBMISSIONS_ID):
        for pb in pendingPBs:
            if pb.submitter == member and pb.getStatus() == PersonalBestStatus.CREATING:
                found = True

        if not found:
            now = datetime.datetime.now()
            now_plus_60 = now + datetime.timedelta(seconds = 60)
            pb = PersonalBest(member, "bossName", "bossGuess", "players", 0, "proof", now_plus_60, PersonalBestStatus.CREATING, 0)        
            pendingPBs.append(pb)

#cancel
@bot.command(name='cancel')
async def event(ctx):
    if (ctx.channel.id == PB_SUBMISSIONS_ID):
        for pb in pendingPBs:
            if pb.submitter == ctx.author and pb.getStatus() == PersonalBestStatus.CREATING:
                await ctx.send(ctx.author.mention + " Submission canceled.")
                pendingPBs.remove(pb)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    raise error


@bot.event
async def on_message(reply):
    await bot.process_commands(reply)
    # If DM, assume its an application
    if isinstance(reply.channel, discord.channel.DMChannel):
        for member in openDms:
            if (member.id == reply.author.id):
                pending_applications = bot.get_channel(PENDING_APPLICATIONS_ID)
                await reply.channel.send("Your application is now under review, you will receieve another message once you have been accepted or declined! Please be patient as this could take up to a few days.")
                message = await pending_applications.send("New application from: " + member.mention + "\n```" + reply.content + "```")
                await message.add_reaction('✔️')
                await message.add_reaction('❌')
                pendingApps.append(message)
                pendingUsers.append(member)
                dmCloseTimes.remove(dmCloseTimes[openDms.index(member)])
                openDms.remove(member)
    # If in pending PBs, assume its for a PB
    for pb in pendingPBs:
        if reply.author == pb.submitter and pb.getStatus() == PersonalBestStatus.CREATING:
            if (reply.channel.id == PB_SUBMISSIONS_ID):
                if pb.getProof() == "proof":
                    # this will never break i promise..
                    if "imgur." in reply.content:
                        pb.setProof(reply.content)
                        await reply.channel.send(reply.author.mention + " Please @mention all members involved, including yourself.")
                    else:
                        await reply.channel.send(reply.author.mention + " Please provide image proof (Imgur only).")

                elif pb.getPlayers() == "players":
                    try:
                        IDs = reply.content.split(" ")
                        names = []
                        for name in IDs:
                            intID = int(''.join(filter(str.isdigit, name)))
                            names.append(intID)

                        pb.setPlayers(names)
                        await reply.channel.send(reply.author.mention + " Please type the name of the content you are submitting for.")
                    except:
                        await reply.channel.send(reply.author.mention + " Please @mention all members involved, including yourself.")

                elif pb.getBossName() == "bossName":
                    if pb.getBossGuess() == "bossGuess":
                        for abbreviation, bossName in bossAbbreviations.items():
                            if abbreviation in reply.content.lower():
                                pb.setBossGuess(bossName)
                        if pb.getBossGuess() == "bossGuess":
                            pb.setBossGuess(difflib.get_close_matches(reply.content, pbBosses, n = 3, cutoff = 0.01)[0])
                        message = await reply.channel.send (reply.author.mention + " Do you mean '" + str(pb.getBossGuess()) + "'? (Yes/No)")
                    else:
                        if reply.content.lower() == "no":
                            pb.setBossGuess("bossGuess")
                            await reply.channel.send(reply.author.mention + " Please type the name of the content you are submitting for.")
                        elif reply.content.lower() == "yes":
                            await reply.channel.send(reply.author.mention + "  Please enter your time in mm:ss format.")
                            pb.setBossName(pb.getBossGuess())
                        else:
                            await reply.channel.send(reply.author.mention + " yes or no only please.")

                elif pb.getTime() == 0:
                    if (re.search("[0-9]{1,3}:[0-5]{1}[0-9]{1}", reply.content) and reply.content[len(reply.content) - 3] == ":"):
                        pb.setTime(reply.content)
                    else:
                        await reply.channel.send(reply.author.mention + " Please enter your time in mm:ss format.")

                # Every message in pb channel from them resets timeout timer to 60seconds
                now = datetime.datetime.now()
                now_plus_60 = now + datetime.timedelta(seconds = 60)
                pb.setTimeoutTime(now_plus_60)
                        
       
                # If time is filled, assume completed PB submission
                if pb.getTime() != 0:
                    await reply.channel.send(reply.author.mention + " Submission complete. Please wait for approval.")
                    guild = get(bot.guilds, id = SERVER_ID)
                    pending_pbs = get(guild.channels, id = PENDING_PBS_ID)
                    message = await pending_pbs.send("New pb submission for: " +  ', '.join(guild.get_member(name).mention for name in pb.getPlayers()) +
                    "\nBoss: " + pb.getBossName() +
                    "\nTime: " + pb.getTime() +
                    "\nProof: " + pb.getProof())

                    await message.add_reaction('✔️')
                    await message.add_reaction('❌')
                    pb.setMessageID(message.id)
                    pb.setStatus(PersonalBestStatus.PENDING)

@bot.event
async def on_raw_reaction_add(payload):
    for message in pendingApps:
        if (message.id == payload.message_id):
            if (payload.member.id != BOT_UID):
                roleIds = []
                reset = False
                for role in payload.member.roles:
                    roleIds.append(role.id)
                if(OFFICIAL_ROLE_ID in roleIds):
                    if (payload.emoji.name == '✔️'):
                        guild = get(bot.guilds, id = SERVER_ID)
                        members_chat = get(guild.channels, id = MEMBERS_CHAT_ID)
                        trial_applications = get(guild.categories , id = TRIAL_APPLICATIONS_CATEGORY_ID)
                        trial_member_role = get(guild.roles, id = TRIAL_MEMBER_ROLE_ID)
                        # Finder Member object
                        user = pendingUsers[pendingApps.index(message)]
                        channel = await user.create_dm()
                        await channel.send("Your application has been accepted!")
                        await user.add_roles(trial_member_role)
                        #create app chan
                        trial_channel = await guild.create_text_channel(user.name + "-application", category=trial_applications)
                        await trial_channel.send(message.content)
                        # collect info for sheet
                        # main rsn
                        splt1 = message.content.split('Main RSN:')[1]
                        split2 = splt1.split('\n')[0]
                        main_rsn = split2.strip(" ")
                        # alt rsn
                        splt1 = message.content.split('Alt RSN (if applicable, 1 max):')[1]
                        split2 = splt1.split('\n')[0]
                        alt_rsn = split2.strip(" ")
                        # preferred name
                        splt1 = message.content.split('Preferred Name (This name will be your name on Discord and will not change):')[1]
                        split2 = splt1.split('\n')[0]
                        preferred_name = split2.strip(" ")
                        # discord hash
                        discord_hash = user.name + "#" + user.discriminator
                        # join date
                        today = date.today()
                        dateToday = today.strftime("%m/%d/%Y")
                        
                        #add to sheet
                        row_number = 0
                        for name in pointsSheet.col_values(1):
                            row_number = row_number + 1
                            if (name == ""):
                                pointsSheet.update_cell(row_number, 1, preferred_name)
                                pointsSheet.update_cell(row_number, 8, dateToday)
                                break


                        column_data = infoSheet.col_values(1)
                        row_location = len(column_data)

                        row = [preferred_name, main_rsn, alt_rsn, discord_hash ,dateToday]
                        infoSheet.insert_row(row, row_location + 1)

                        # set their discord nick to pref name - note this doesnt work for server owners for some reason.
                        await user.edit(nick=preferred_name)

                        # send members chat welcome message
                        await members_chat.send("Please welcome " + user.mention + " to Sanity!")
                        reset = True
                        
                    elif (payload.emoji.name == '❌'):
                        user = pendingUsers[pendingApps.index(message)]
                        channel = await user.create_dm()
                        await channel.send("Your application has been declined. Please private message " + payload.member.name + " if you wish to find out why.")
                        reset = True
                    
                    try:
                        if reset:
                            await message.clear_reaction('❌')
                            await message.clear_reaction('✔️')
                            pendingUsers.remove(pendingUsers[pendingApps.index(message)])
                            pendingApps.remove(message)
                    except:
                        pass
                    

    for pb in pendingPBs:
        if payload.message_id == pb.getMessageID() and pb.getStatus() == PersonalBestStatus.PENDING:
            if (payload.member.id != BOT_UID):
                roleIds = []
                for role in payload.member.roles:
                    roleIds.append(role.id)
                if(OFFICIAL_ROLE_ID in roleIds or payload.member.id == DEV_UID):
                    if (payload.emoji.name == '✔️'):
                        await put_pb(pb.getBossName(), pb.getNames(), pb.getProof(), pb.getTime())
                        await message.clear_reaction('✔️')
                        await message.clear_reaction('❌')
                        pendingPBs.remove(pb)
                        pbSubmittedUpdate[0] = True
                    elif (payload.emoji.name == '❌'):
                        user = pb.getSubmitter()
                        await message.delete()
                        channel = await user.create_dm()
                        await channel.send("Your pb submission has been declined. Please private message " + payload.member.name + " if you wish to find out why.")
                        pendingPBs.remove(pb)
                

#insert pb to database & spreadsheet
async def put_pb(bossname, players, proof, time):
    playernames = ""
    if type(players) == list:
        players.sort
        playernames = ','.join(str(player) for player in players)
    else:
        playernames = str(players[0])

    #playernames = str(players)

    #database
    boto3_client.put_item(TableName='Submitted_PBs', Item={
        'SubID':{
           'N': str(len(pbDatabase[0]) + 9)
        },
        'BossName':{
            'S': bossname
        },
        'Players':{
            'S': playernames
            },
        'Proof':{
            'S': proof
            },
        'Time':{
            'S': time
                }
            }
        )

    #spreadsheet
    column_data = pbLogSheet.col_values(1)
    row_location = len(column_data)

    for i in range(len(players)):
        row_to_update = i + row_location + 1
        pbLogSheet.update_cell(row_to_update, 1, str(await convertPlayers(players[i])))
        pbLogSheet.update_cell(row_to_update, 2, bossname)
        pbLogSheet.update_cell(row_to_update, 3, convertForSheet(len(players)))
        pbLogSheet.update_cell(row_to_update, 4, time)
        pbLogSheet.update_cell(row_to_update, 5, proof)
        pbLogSheet.update_cell(row_to_update, 7, row_to_update - 1)


        #row = [str(await convertPlayers(players[i])), bossname, convertForSheet(len(players)), time, proof, "", i + row_location]
        #pbLogSheet.insert_row(row, i + row_location + 1)

    get_db()


# Get pbs from database and store them locally
def get_db():
    table = boto3_resource.Table('Submitted_PBs')
    response = table.scan()
    pbDatabase.clear()
    pbDatabase.append(response['Items'])

    inc = 0
    # Turn mm:ss strings into datetime
    while inc < len(pbDatabase[0]):
        # If no :, assume already converted to seconds
        if (":" in  str(pbDatabase[0][inc]['Time'])):
            m,s = str(pbDatabase[0][inc]['Time']).split(':')
            #Convert to seconds for sorting later on
            pbDatabase[0][inc]['Time'] = datetime.timedelta(minutes=int(m),seconds=int(s)).total_seconds()
        inc += 1

# update pb leaderboards channel
async def update_pbs():
    get_db()
    #ugly af... but for whatever reason declaring them at same time causing issues 
    cox_solo = []
    cox_cm_solo = []
    cox_cm_trio = []
    cox_cm_5 = []
    tob_duo = []
    tob_trio = []
    tob_4 = []
    tob_5 = []
    inferno = []
    fight_caves = []
    six_jads = []
    c_gauntlet = []
    categories = [cox_solo, cox_cm_solo, cox_cm_trio, cox_cm_5, tob_duo, tob_trio, tob_4, tob_5, inferno, fight_caves, six_jads, c_gauntlet]
    inc = 0

    # Sort pbs into individual arrays - needs a cleaner solution tbh 
    while inc < len(pbDatabase[0]):
        if pbDatabase[0][inc]['BossName'] == "Chambers of Xeric (Challenge mode)":
            if pbDatabase[0][inc]['Players'].count(",") == 0:
                cox_cm_solo.append(pbDatabase[0][inc])
            if pbDatabase[0][inc]['Players'].count(",") == 2:
                cox_cm_trio.append(pbDatabase[0][inc])
            if pbDatabase[0][inc]['Players'].count(",") == 4:
                cox_cm_5.append(pbDatabase[0][inc])
        elif pbDatabase[0][inc]['BossName'] == "Chambers of Xeric":
            if pbDatabase[0][inc]['Players'].count(",") == 0:
                cox_solo.append(pbDatabase[0][inc])
        elif pbDatabase[0][inc]['BossName'] == "Theatre of Blood":
            if pbDatabase[0][inc]['Players'].count(",") == 1:
                tob_duo.append(pbDatabase[0][inc])
            if pbDatabase[0][inc]['Players'].count(",") == 2:
                tob_trio.append(pbDatabase[0][inc])
            if pbDatabase[0][inc]['Players'].count(",") == 3:
                tob_4.append(pbDatabase[0][inc])
            if pbDatabase[0][inc]['Players'].count(",") == 4:
                tob_5.append(pbDatabase[0][inc])
        elif pbDatabase[0][inc]['BossName'] == "Fight Caves":
            if pbDatabase[0][inc]['Players'].count(",") == 0:
                fight_caves.append(pbDatabase[0][inc])
        elif pbDatabase[0][inc]['BossName'] == "6 Jads":
            if pbDatabase[0][inc]['Players'].count(",") == 0:
                six_jads.append(pbDatabase[0][inc])
        elif pbDatabase[0][inc]['BossName'] == "Corrupted Gauntlet":
            if pbDatabase[0][inc]['Players'].count(",") == 0:
                c_gauntlet.append(pbDatabase[0][inc])
        elif pbDatabase[0][inc]['BossName'] == "The Inferno":
            if pbDatabase[0][inc]['Players'].count(",") == 0:
                inferno.append(pbDatabase[0][inc])

        inc += 1

    inc = 0
    for cat in categories:
        cat.sort(key=sort_key)

        # Used to find indexs of non duplicate pb entries from same people. These are already sorted by time so keeping the first entry of each person works
        # Also used to check UID for if sanity member or not
        players = []
        valid_indexs = []
        invalid_indexs = []
        index = 0
        for pb in cat:
            ids = []
            if (pb['Players'] not in players):
                ids.append(pb['Players'].split(","))
                players.append(pb['Players'])
                guild = get(bot.guilds, id = SERVER_ID)
                
                try:
                    for uids in ids:
                        if isinstance(uids, list):
                            nonMemberFound = True
                            for uid in uids:
                                nonMemberFound = True
                                guild = get(bot.guilds, id = SERVER_ID)
                                member = guild.get_member(int(uid))

                                roles = member.roles
                            
                                for role in roles:
                                    if str(role.id) in MEMBERS_ROLES:
                                        nonMemberFound = False
                                    
                            
                                if nonMemberFound:
                                    if index not in invalid_indexs:
                                        invalid_indexs.append(index)
                                        if index in valid_indexs:
                                            valid_indexs.remove(index)
                                else:
                                    if index not in invalid_indexs:
                                        if index not in valid_indexs:
                                            valid_indexs.append(index)
                        else:  
                            guild = get(bot.guilds, id = SERVER_ID)
                            member = guild.get_member(int(uids))

                            roles = member.roles
                            for role in roles:
                                if str(role.id) in MEMBERS_ROLES:
                                    valid_indexs.append(index)
                                else:
                                    invalid_indexs.append(index)
                except:
                    #Non sanity member as not in discord (uid lookup failed)
                    if index not in invalid_indexs:
                        invalid_indexs.append(index)
                        if index in valid_indexs:
                            valid_indexs.remove(index)
                    pass
 
            index += 1

        for i in range(3):
            if (len(valid_indexs) > i):
                if top3Pbs[inc][i] != cat[valid_indexs[i]]:
                    pbsRequireUpdate[0] = True
                    top3Pbs[inc][i] = cat[valid_indexs[i]]
            elif top3Pbs[inc][i] != 0:
                top3Pbs[inc][i] = 0
                pbsRequireUpdate[0] = True
        
        
        inc += 1

    if pbsRequireUpdate[0]:
        await refreshPbChannel()


async def refreshPbChannel():
    lastRefresh[0] = datetime.datetime.now() + datetime.timedelta(minutes = 5)
    guild = get(bot.guilds, id = SERVER_ID)
    pb_leaderboard = get(guild.channels, id = PB_LEADERBOARD_ID)
    sizes = ["Solo", "Solo", "Trio", "5man", "Duo", "Trio", "4man", "5man", "Inferno", "Fight Caves", "6 Jads", "Corrupted Gauntlet"]
    await pb_leaderboard.purge(limit = 200)
    # PBs building in discord
    for category in top3Pbs:
        if top3Pbs.index(category) == 0:
            await pb_leaderboard.send(file=discord.File('resources/banners/cox.png'))
        elif top3Pbs.index(category) == 1:
            await pb_leaderboard.send(file=discord.File('resources/banners/cm.png'))
        elif top3Pbs.index(category) == 4:
            await pb_leaderboard.send(file=discord.File('resources/banners/tob.png'))
        elif top3Pbs.index(category) == 8:
            await pb_leaderboard.send(file=discord.File('resources/banners/inferno.png'))
        elif top3Pbs.index(category) == 9:
            await pb_leaderboard.send(file=discord.File('resources/banners/fight_caves.png'))
        elif top3Pbs.index(category) == 11:
            await pb_leaderboard.send(file=discord.File('resources/banners/c_gauntlet.png'))

        await addPbToChannel(sizes[top3Pbs.index(category)], category, pb_leaderboard)


    pbsRequireUpdate[0] = False

# Sort array by time
def sort_key(pb):
    return pb['Time']


# Turn seconds into h:mm:ss/mm:ss/m:ss 
def convertTime(inputTime):
    intTime = int(inputTime)
    m, s = divmod(intTime, 60)
    h, m = divmod(m, 60)

    if (intTime >= 3600):
        return(f'{h:d}:{m:02d}:{s:02d}')
    elif (intTime >= 600):
        return(f'{m:02d}:{s:02d}')
    else:
        return(f'{m:01d}:{s:02d}')

# Used to turn a a single or list of discord UIDs into a comma sepparated string of their nicknames, if no nickname, will use their default discord name
async def convertPlayers(players):
    guild = get(bot.guilds, id = SERVER_ID)
    playerNicks = []
    
    if "," in str(players):
        players = players.split(",")
        for player in players:
            intID = int(player)
            try:
                member = guild.get_member(intID)
                playerNicks.append(member.display_name)
            except:
                print("[WARNING] Id thrown when trying to find disord member: " + str(intID))
    else:
        member = guild.get_member(int(players))
        return member.display_name

    return ", ".join(playerNicks)

# Add pb to channel
async def addPbToChannel(size, list, channel):
    # Catch for false data we filled with earlier
    if list[0] != 0:
        emoji = discord.utils.get(bot.emojis, name='bullet')
        message = (str(emoji) + " **" + size + "**")
        proof = ""
        if list[0] != 0:
            message += "```yaml"
            message += "\n1st: " + str(convertTime(list[0]['Time'])) + " - " + str(await convertPlayers(list[0]['Players']))
            proof += "<" + str(list[0]['Proof']) + "\>"
        if list[1] != 0:
            message += "\n2nd: " + str(convertTime(list[1]['Time'])) + " - " + str(await convertPlayers(list[1]['Players']))
            proof += "\n<" + str(list[1]['Proof']) + "\>"
        if list[2] != 0:
            message += "\n3rd: " + str(convertTime(list[2]['Time'])) + " - " + str(await convertPlayers(list[2]['Players']))
            proof += "\n<" + str(list[2]['Proof']) + "\>"
        if (proof != ""):
            message += "```"
            message += proof
        await channel.send(message)
    else:
        await channel.send("*No PBs found for category*")

# Used for turning pb group size into strings to match the sheets used
def convertForSheet(length):
    if length == 1:
        return "Solo"
    elif length == 2:
        return "Duo"
    elif length == 3:
        return "Trio"
    elif length == 4:
        return "Quad"
    elif length == 5:
        return "5 Man"
    else:  
        return "0"

# Used to download PBs from sheets and insert into db. The data on sheets does need to be edited slightly before using this. Will need updating if needs running in the future
async def download_sheets():
    print("download started")
    completeSheet = pbLogSheet.get_all_values()
    skip = 0
    index = 1
    for entry in completeSheet:
        if (skip != 0):
            skip -= 1
        if skip == 0:
            if entry[2] == "Solo":
                playername = entry[0]
                bossname = entry[1]
                time = entry[3]
                proof = entry[4]

            elif entry[2] == "Duo":
                playername = entry[0]
                playername += "," + completeSheet[completeSheet.index(entry) + 1][0]
                bossname = entry[1]
                time = entry[3]
                proof = entry[4]
                skip = 2

            elif entry[2] == "Trio":
                playername = entry[0]
                playername += "," + completeSheet[completeSheet.index(entry) + 1][0]
                playername += "," + completeSheet[completeSheet.index(entry) + 2][0]
                bossname = entry[1]
                time = entry[3]
                proof = entry[4]
                skip = 3

            elif entry[2] == "Quad":
                playername = entry[0]
                playername += "," + completeSheet[completeSheet.index(entry) + 1][0]
                playername += "," + completeSheet[completeSheet.index(entry) + 2][0]
                playername += "," + completeSheet[completeSheet.index(entry) + 3][0]
                bossname = entry[1]
                time = entry[3]
                proof = entry[4]
                skip = 4
            
            elif entry[2] == "5 Man":
                playername = entry[0]
                playername += "," + completeSheet[completeSheet.index(entry) + 1][0]
                playername += "," + completeSheet[completeSheet.index(entry) + 2][0]
                playername += "," + completeSheet[completeSheet.index(entry) + 3][0]
                playername += "," + completeSheet[completeSheet.index(entry) + 4][0]
                bossname = entry[1]
                time = entry[3]
                proof = entry[4]
                skip = 5
            
            #regex was tilting me for this one ^([^:]*.[^:]*).*$ should work with re.sub but not working brainfried cba
            timepart1 = time.split(":")[0]
            timepart2 = time.split(":")[1]
            timepart3 = timepart2.split(":")[0]
            
            time = timepart1 + ":" + timepart3

            # convert playernames to uids and then we can insert data to the database
            if "," in playername:
                namesList = playername.split(",")
                uidList = []
                for name in namesList:
                    try:
                        uidList.append(str(discord.utils.get(bot.get_all_members(), display_name = name).id))
                    except:
                        print(name)
                        break

                uidList.sort()      
                uid = ",".join(uidList)
            else:
                try:
                    uid = discord.utils.get(bot.get_all_members(), display_name = playername).id
                except:
                    print(playername)
                    break
            
            print(bossname, uid, proof, time)
            await put_pb(bossname, uid, proof, time)
            
        index += 1
    
    print("complete download")

            
#cleardb used to empty everything from the database, usually used just before repopulating it from sheets.
#@bot.command(name='cleardb')
#@commands.has_role(OFFICIAL_ROLE_ID)
#async def event(ctx):
#    scan = boto3_resource.Table('Submitted_PBs').scan()
#    table = boto3_resource.Table('Submitted_PBs')

#    with table.batch_writer() as batch:
#        for item in scan['Items']:
#            batch.delete_item(
#            Key={
#                'SubID': item['SubID']
#                }
#            )
#    print("db cleared")
#    await update_pbs()


bot.run(TOKEN)