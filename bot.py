from logging import lastResort
from sre_constants import CATEGORY_DIGIT
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
from dateutil import relativedelta
import boto3
import re
from dotenv import load_dotenv
from pathlib import Path
import os
import difflib

from PersonalBest.PersonalBest import PersonalBest
from PersonalBest.PersonalBestBossName import PersonalBestBossName
from PersonalBest.PersonalBestStatus import PersonalBestStatus
from PersonalBest.PersonalBestCategory import PersonalBestCategory
from PersonalBest.PersonalBestScale import PersonalBestScale
from PersonalBest.PersonalBestProfile import PersonalBestProfile
from PersonalBest.PersonalBestDiaryLevel import PersonalBestDiaryLevel

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
activity = discord.Game(name="Sanity Bot v2 by jajack#2361")
bot = commands.Bot(command_prefix=os.getenv("DISCORD_PREFIX"), activity = activity, case_insensitive=True, intents=intents)

# discord vars
BOT_UID = int(os.getenv("DISCORD_BOT_UID"))
DEV_UID = int(os.getenv("DISCORD_DEV_UID"))
NON_CLANNIE_UID = int(os.getenv("DISCORD_NON_CLANNIE_UID"))

#sanity disc
PB_LEADERBOARD_ID = int(os.getenv("SERVER_PB_LEADERBOARD_ID"))
PB_SUBMISSIONS_ID = int(os.getenv("SERVER_PB_SUBMISSIONS_ID"))
PENDING_PBS_ID = int(os.getenv("SERVER_PENDING_PBS_ID"))
SERVER_ID = int(os.getenv("SERVER_SERVER_ID"))
OFFICIAL_ROLE_ID = int(os.getenv("SERVER_OFFICIAL_ROLE_ID"))
MEMBERS_ROLES = os.getenv("SERVER_MEMBERS_ROLES").split(",")
BOT_COMMANDS_ID = int(os.getenv("SERVER_BOT_COMMANDS_ID"))

# Setup Database Connection
boto3_client = boto3.client('dynamodb',aws_access_key_id=os.getenv("AWS_ACCESS"), aws_secret_access_key=os.getenv("AWS_SECRET"), region_name=os.getenv("AWS_REGION"))
boto3_resource = boto3.resource('dynamodb',aws_access_key_id=os.getenv("AWS_ACCESS"), aws_secret_access_key=os.getenv("AWS_SECRET"), region_name=os.getenv("AWS_REGION"))

# List of PersonalBest objects who have an open pb submission
pendingPBs = []
# List of PersonalBest objects downloaded from the AWS database
pbDatabase = []
# List of approved PersonalBest objects that need to be added to the database/google sheets
approvedPbs = []

# List of PersonalBestCategory objects for storing PersonalBest objects, to manipulate for hiscores
pbCategories = [PersonalBestCategory(PersonalBestBossName.CHAMBERS_OF_XERIC_CHALLENGE_MODE, PersonalBestScale.SOLO), PersonalBestCategory(PersonalBestBossName.CHAMBERS_OF_XERIC_CHALLENGE_MODE, PersonalBestScale.TRIO), PersonalBestCategory(PersonalBestBossName.CHAMBERS_OF_XERIC_CHALLENGE_MODE, PersonalBestScale.FIVE_MAN), 
                PersonalBestCategory(PersonalBestBossName.THEATRE_OF_BLOOD, PersonalBestScale.DUO), PersonalBestCategory(PersonalBestBossName.THEATRE_OF_BLOOD, PersonalBestScale.TRIO), PersonalBestCategory(PersonalBestBossName.THEATRE_OF_BLOOD, PersonalBestScale.FOUR_MAN), PersonalBestCategory(PersonalBestBossName.THEATRE_OF_BLOOD, PersonalBestScale.FIVE_MAN), 
                PersonalBestCategory(PersonalBestBossName.INFERNO, PersonalBestScale.SOLO), 
                PersonalBestCategory(PersonalBestBossName.FIGHT_CAVES, PersonalBestScale.SOLO), 
                PersonalBestCategory(PersonalBestBossName.SIX_JADS, PersonalBestScale.SOLO), 
                PersonalBestCategory(PersonalBestBossName.CORRUPTED_GAUNTLET, PersonalBestScale.SOLO),
                PersonalBestCategory(PersonalBestBossName.TOMBS_OF_AMASCUT, PersonalBestScale.SOLO),
                PersonalBestCategory(PersonalBestBossName.TOMBS_OF_AMASCUT, PersonalBestScale.FOUR_MAN),
                PersonalBestCategory(PersonalBestBossName.FANG_KIT, PersonalBestScale.SOLO)]

top3Pbs = [PersonalBestCategory(PersonalBestBossName.CHAMBERS_OF_XERIC_CHALLENGE_MODE, PersonalBestScale.SOLO), PersonalBestCategory(PersonalBestBossName.CHAMBERS_OF_XERIC_CHALLENGE_MODE, PersonalBestScale.TRIO), PersonalBestCategory(PersonalBestBossName.CHAMBERS_OF_XERIC_CHALLENGE_MODE, PersonalBestScale.FIVE_MAN), 
            PersonalBestCategory(PersonalBestBossName.THEATRE_OF_BLOOD, PersonalBestScale.DUO), PersonalBestCategory(PersonalBestBossName.THEATRE_OF_BLOOD, PersonalBestScale.TRIO), PersonalBestCategory(PersonalBestBossName.THEATRE_OF_BLOOD, PersonalBestScale.FOUR_MAN), PersonalBestCategory(PersonalBestBossName.THEATRE_OF_BLOOD, PersonalBestScale.FIVE_MAN), 
            PersonalBestCategory(PersonalBestBossName.INFERNO, PersonalBestScale.SOLO), 
            PersonalBestCategory(PersonalBestBossName.FIGHT_CAVES, PersonalBestScale.SOLO), 
            PersonalBestCategory(PersonalBestBossName.SIX_JADS, PersonalBestScale.SOLO), 
            PersonalBestCategory(PersonalBestBossName.CORRUPTED_GAUNTLET, PersonalBestScale.SOLO),
            PersonalBestCategory(PersonalBestBossName.TOMBS_OF_AMASCUT, PersonalBestScale.SOLO),
            PersonalBestCategory(PersonalBestBossName.TOMBS_OF_AMASCUT, PersonalBestScale.FOUR_MAN),
                PersonalBestCategory(PersonalBestBossName.FANG_KIT, PersonalBestScale.SOLO)]

# List of PersonalBestProfile objects for building the personal diary log
pbProfiles = []

# List of Abbreviations for PB Bosses that auto predictor could miss
bossAbbreviations = {
  "tob": "Theatre of Blood",
  "cox": "Chambers of Xeric",
  "cm": "Chambers of Xeric (Challenge mode)",
  "cg": "Corrupted Gauntlet",
  "toa": "Tombs of Amascut"
}

# These are stored in seconds
diaryTimes = {
    "Chambers of Xeric (Challenge mode) Solo" : [3000, 2400, 2160, 1980, 1800],
    "Chambers of Xeric (Challenge mode) Trio" : [1680, 1590, 1500, 1410, 1320],
    "Chambers of Xeric (Challenge mode) 5man" : [1620, 1500, 1410, 1320, 1230],
    "Theatre of Blood Duo" : [1800, 1620, 1470, 1395, 1350],
    "Theatre of Blood Trio" : [1260, 1170, 1080, 1005, 960],
    "Theatre of Blood 4man" : [1170, 1050, 945, 885, 840],
    "Theatre of Blood 5man" : [1050, 960, 885, 825, 780],
    "The Inferno Solo" : [5400, 4200, 3900, 3300, 3000],
    "Fight Caves Solo" : [1980, 1800, 1650, 1530, 1455],
    "6 Jads Solo" : [3600],
    "Corrupted Gauntlet Solo" : [720, 600, 510, 420, 345],
    "Tombs of Amascut Solo" : [1800, 1620, 1440, 1335, 1260],
    "Tombs of Amascut 4man" : [1680, 1500, 1395, 1335, 1290],
    "Fang Kit Solo" : [99999999999999]
}

appsOpen = [False]
pbsRequireUpdate = [False]
pbSubmittedUpdate = [False]
lastRefresh = [datetime.datetime.now()]

@bot.event
async def on_ready():
    for cat in top3Pbs:
        cat.addPb(0)
        cat.addPb(1)
        cat.addPb(2)
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
    if len(approvedPbs) > 0:
        pb = approvedPbs[0]
        await put_pb(pb.getBossName().value, pb.getPlayers(), pb.getProof(), pb.getTime())
        approvedPbs.remove(pb)
        pbSubmittedUpdate[0] = True

    if pbSubmittedUpdate[0] == True and len(approvedPbs) == 0:
        pbSubmittedUpdate[0] = False
        await update_pbs()
        

@tasks.loop(seconds=30.0)
async def checkStoredDateTimes():
    now = datetime.datetime.now()

    for pb in pendingPBs:
        if pb.getTimeoutTime() < now:
            if pb.getStatus() == PersonalBestStatus.CREATING:
                guild = get(bot.guilds, id = SERVER_ID)
                pb_submissions = get(guild.channels, id = PB_SUBMISSIONS_ID)
                member = pb.getSubmitter()
                pb.addMessageToDelete(await pb_submissions.send(member.mention + " Submission timed out. Please start a new submission."))
                pendingPBs.remove(pb)
                for message in pb.getMessagesToDelete():
                    await deleteMessage(message)
                for message in pb.getMessagesToKeep():
                    await deleteMessage(message)

@bot.command(name='refreshpbs')
async def event(ctx):
    if ctx.channel.id == 847952282972323870:
        await ctx.channel.send("Refresh started...")
        for pbCategory in pbCategories:
            pbCategory.clearPbList()

        for cat in top3Pbs:
            cat.clearPbList()
            cat.addPb(0)
            cat.addPb(1)
            cat.addPb(2)

        await update_pbs()
        await ctx.channel.send("Refresh complete.")

#apply
@bot.command(name='apply')
async def event(ctx):
    await ctx.channel.send("https://imgur.com/a/mGgieUB")

#pb
@bot.command(name='pb')
async def event(ctx):
    member = ctx.author
    pbFound = False
    if (member.id != BOT_UID and ctx.channel.id == PB_SUBMISSIONS_ID):
        for pb in pendingPBs:
            if pb.getSubmitter() == member and pb.getStatus() == PersonalBestStatus.CREATING:
                pbFound = True
        if not pbFound:
            now = datetime.datetime.now()
            now_plus_60 = now + datetime.timedelta(seconds = 60)
            pb = PersonalBest("bossName", "players", 0, "proof", PersonalBestScale.UNKNOWN, member, "bossGuess", PersonalBestStatus.CREATING, now_plus_60)      
            pendingPBs.append(pb)
            pb.addMessageToDelete(ctx.message)

#cancel
@bot.command(name='cancel')
async def event(ctx):
    if (ctx.channel.id == PB_SUBMISSIONS_ID):
        for pb in pendingPBs:
            if pb.getSubmitter() == ctx.author and pb.getStatus() == PersonalBestStatus.CREATING:
                pb.addMessageToDelete(await ctx.send(ctx.author.mention + " Submission canceled."))
                pb.addMessageToDelete(ctx.message)
                for message in pb.getMessagesToDelete():
                    await deleteMessage(message)
                for message in pb.getMessagesToKeep():
                    await deleteMessage(message)
                pendingPBs.remove(pb)

#leaderboard
@bot.command(name='leaderboard')
async def event(ctx, *, arg = ""):
    if ctx.channel.id == BOT_COMMANDS_ID:
        maxPbs = 15
        if arg.isnumeric():
            if int(arg) > 40:
                maxPbs = 40
            else:
                maxPbs = int(arg)


        pbProfiles.sort(key=lambda x: x.getPoints())
        pbProfiles.reverse()

        embed = discord.Embed(title= "Sanity Diary Points Leaderboard")
        embed.set_author(name="Sanity Bot", icon_url="https://i.imgur.com/AnpyKOY.png")

        value = ""
        
        for i in range(0, maxPbs):
            value += str(i + 1) + ") " + str(pbProfiles[i].getMember()) + " - " + str(pbProfiles[i].getPoints()) + "/182\n"
        
        
        embed.add_field(name = "Leaderboard", value = value, inline = False)
            
        embed.set_footer(text = "Sanity Bot - PB Diary Point Leaderboard")
        await ctx.send(embed = embed)

    else:
        channel = bot.get_channel(BOT_COMMANDS_ID)
        await ctx.send("Please use me in " + channel.mention)

#profile
@bot.command(name='diary')
async def event(ctx, *, arg = ""):
    if ctx.channel.id == BOT_COMMANDS_ID:
        nameFound = False
        points = 0
        emoji = discord.utils.get(bot.emojis, name='bullet')

        name = await getName(ctx, arg)

        for profile in pbProfiles:
            if profile.getMember().lower() == name.lower():
                name = profile.getMember()
                nameFound = True
                points = profile.getPoints()
                embed = discord.Embed(title= name + "'s Diary Profile - Total points: " + str(points) + "/182")
                embed.set_author(name="Sanity Bot", icon_url="https://i.imgur.com/AnpyKOY.png")

                for bossname in PersonalBestBossName:
                    value = ""
                    for scale in PersonalBestScale:
                        for pb in profile.getPbList():
                            if pb.getBossName().value == bossname.value:
                                if pb.getScale() == scale:
                                    value +=  "**" + scale.value + "**"
                                    value +=  " - " + convertTime(pb.getTime()) + " - Diary level: " + pb.getDiaryLevel().value + "\n"
                                    value +=  pb.getProof() + "\n\n"
                    if value != "":
                        embed.add_field(name = str(emoji) + " " + bossname.value, value = value, inline = False)

                    
                embed.set_footer(text = "Sanity Bot - PB Diary Profile")
                await ctx.send(embed = embed)
        
        if not nameFound:
                await ctx.send(name + " was not found in the database.")
    else:
        channel = bot.get_channel(BOT_COMMANDS_ID)
        await ctx.send("Please use me in " + channel.mention)

#age
@bot.command(name='age')
async def event(ctx, *, arg = ""):
    completeSheet = pointsSheet.get_all_values()
    nameFound = False
   
    name = await getName(ctx, arg)

    nameColumnNum = completeSheet[0].index("Name")
    dateColumnNum = completeSheet[0].index("Join date")
    for entry in completeSheet:
        if entry[nameColumnNum].lower() == name.lower():
            name = entry[nameColumnNum]
            if entry[dateColumnNum].count("/") == 2:
                month = entry[dateColumnNum].split("/")[0]  
                day = entry[dateColumnNum].split("/")[1]
                year = entry[dateColumnNum].split("/")[2]
                joinDate = date(int(year), int(month), int(day))
                todayDate = date.today()
                diff = relativedelta.relativedelta(joinDate, todayDate)
                timeAgo = ""

                if abs(diff.years) > 0:
                    timeAgo += str(abs(diff.years)) + " year(s), "
                    timeAgo += str(abs(diff.months)) + " month(s), "
                    timeAgo += str(abs(diff.days)) + " day(s)"
                elif abs(diff.months) > 0:
                    timeAgo += str(abs(diff.months)) + " month(s), "
                    timeAgo += str(abs(diff.days)) + " day(s)"
                else: 
                    timeAgo += str(abs(diff.days)) + " day(s)"


                await ctx.send(name + " joined on: " + str(joinDate) + ". This was " + timeAgo + " ago.")

            else: 
                await ctx.send(name + " joined on: unknown.")

            nameFound = True

    if not nameFound:
        await ctx.send(name + " was not found in the spreadsheet.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    raise error


@bot.event
async def on_message(reply):
    await bot.process_commands(reply)
    # If in pending PBs, assume its for a PB
    for pb in pendingPBs:
        if reply.author == pb.getSubmitter() and pb.getStatus() == PersonalBestStatus.CREATING:
            if (reply.channel.id == PB_SUBMISSIONS_ID):
                if pb.getProof() == "proof":
                    # this will never break i promise..
                    if "imgur." in reply.content and " " not in reply.content:
                        pb.setProof(reply.content)
                        pb.addMessageToKeep(reply)
                        pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " Please @mention all members involved, including yourself."))
                    else:
                        pb.addMessageToDelete(message = await reply.channel.send(reply.author.mention + " Please provide image proof (Imgur only)."))
                        pb.addMessageToDelete(reply)
                elif pb.getPlayers() == "players":
                    try:
                        IDs = reply.content.split(" ")
                        names = []
                        for name in IDs:
                            intID = int(''.join(filter(str.isdigit, name)))
                            names.append(intID)

                        pb.setPlayers(names)
                        pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " Please type the name of the content you are submitting for."))
                        pb.addMessageToKeep(reply)
                    except:
                        pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " Please @mention all members involved, including yourself."))
                        pb.addMessageToDelete(reply)
                elif pb.getBossName() == "bossName":
                    pb.addMessageToDelete(reply)
                    if pb.getBossGuess() == "bossGuess":                        
                        for abbreviation, bossName in bossAbbreviations.items():
                            if abbreviation in reply.content.lower():
                                pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " Do you mean '" + str(bossName) + "'? (Yes/No)"))
                                pb.setBossGuess(convertToPersonalBestBossName(bossName))
                        if pb.getBossGuess() == "bossGuess":
                            pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " Do you mean '" + str(difflib.get_close_matches(reply.content, [e.value for e in PersonalBestBossName], n = 3, cutoff = 0.01)[0]) + "'? (Yes/No)"))
                            pb.setBossGuess(difflib.get_close_matches(reply.content, [e.value for e in PersonalBestBossName], n = 3, cutoff = 0.01)[0])
                    else:
                        if reply.content.lower() == "no":
                            pb.setBossGuess("bossGuess")
                            pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " Please type the name of the content you are submitting for."))
                        elif reply.content.lower() == "yes":
                            pb.addMessageToDelete(await reply.channel.send(reply.author.mention + "  Please enter your time in mm:ss format."))
                            if isinstance(pb.getBossGuess(), str):
                                pb.setBossGuess(convertToPersonalBestBossName(pb.getBossGuess()))
                            pb.setBossName(pb.getBossGuess())
                        else:
                            pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " yes or no only please."))
                elif pb.getTime() == 0:
                    pb.addMessageToDelete(reply)
                    if (re.search("[0-9]{1,3}:[0-5]{1}[0-9]{1}", reply.content) and reply.content[len(reply.content) - 3] == ":"):
                        pb.setTime(reply.content)
                    else:
                        pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " Please enter your time in mm:ss format."))
                    
                # Every message in pb channel from the submitter resets timeout timer to 60seconds
                now = datetime.datetime.now()
                now_plus_60 = now + datetime.timedelta(seconds = 60)
                pb.setTimeoutTime(now_plus_60)
                        
                # If time is filled, assume completed PB submission
                if pb.getTime() != 0:
                    pb.addMessageToDelete(await reply.channel.send(reply.author.mention + " Submission complete. Please wait for approval."))
                    guild = get(bot.guilds, id = SERVER_ID)
                    pending_pbs = get(guild.channels, id = PENDING_PBS_ID)
                    message = await pending_pbs.send("New pb submission for: " +  ', '.join(guild.get_member(name).mention for name in pb.getPlayers()) +
                    "\nBoss: " + pb.getBossName().value +
                    "\nTime: " + pb.getTime() +
                    "\nProof: " + pb.getProof())

                    await message.add_reaction('✔️')
                    await message.add_reaction('❌')
                    pb.setMessageID(message.id)
                    pb.setStatus(PersonalBestStatus.PENDING)
                    pb.setScale(calculateScale(pb.getPlayers()))
                    for message in pb.getMessagesToDelete():
                        await deleteMessage(message)
                    
@bot.event
async def on_raw_reaction_add(payload):              
    for pb in pendingPBs:
        if payload.message_id == pb.getMessageID() and pb.getStatus() == PersonalBestStatus.PENDING:
            if payload.member.id != BOT_UID:
                roleIds = []
                for role in payload.member.roles:
                    roleIds.append(role.id)
                if(OFFICIAL_ROLE_ID in roleIds or payload.member.id == DEV_UID):
                    channel = bot.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)
                    if (payload.emoji.name == '✔️'):
                        await message.clear_reaction('✔️')
                        await message.clear_reaction('❌')
                        approvedPbs.append(pb)
                        pendingPBs.remove(pb)
                    elif (payload.emoji.name == '❌'):
                        user = pb.getSubmitter()
                        await message.delete()
                        channel = await user.create_dm()
                        await channel.send("Your pb submission has been declined. Please private message " + payload.member.name + " if you wish to find out why.")
                        pendingPBs.remove(pb)
                        for message in pb.getMessagesToKeep():
                            await deleteMessage(message)
                
#insert pb to database & spreadsheet
async def put_pb(bossname, players, proof, time):
    channel_id = 847952282972323870
    channel = bot.get_channel(channel_id)
    playernames = ""
    if type(players) == list:
        players.sort
        playernames = ','.join(str(player) for player in players)
    else:
        playernames = str(players[0])

    # used when updating via sheets
    #playernames = str(players)

    #database
    try:
        boto3_client.put_item(TableName='Submitted_PBs', Item={
            'SubID':{
            'N': str(len(pbDatabase))
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
    except: 
        await channel.send("Error during database insertion for PB: " + str(proof))
    

    #spreadsheet
    column_data = pbLogSheet.col_values(1)
    row_location = len(column_data)

    try:
        for i in range(len(players)):
            row_to_update = i + row_location + 1
            pbLogSheet.update_cell(row_to_update, 1, str(await convertPlayers(players[i])))
            pbLogSheet.update_cell(row_to_update, 2, bossname)
            pbLogSheet.update_cell(row_to_update, 3, convertForSheet(len(players)))
            pbLogSheet.update_cell(row_to_update, 4, time)
            pbLogSheet.update_cell(row_to_update, 5, proof)
            pbLogSheet.update_cell(row_to_update, 7, row_to_update - 1)
    except: 
        await channel.send("Error during spreadsheet insertion for PB: " + str(proof))

    get_db()


# Get pbs from database and store them locally
def get_db():
    table = boto3_resource.Table('Submitted_PBs')
    response = table.scan()
    pbDatabase.clear()

    awsDownload = (response['Items'])
    for pb in awsDownload:
        if pb['BossName'] != "" and pb['Players'] != "" and pb['Time'] != "" and pb['Proof'] != "":
            players = pb['Players'].split(",")
            players.sort()
            players = ','.join(str(player) for player in players)
            pbToAdd = PersonalBest(convertToPersonalBestBossName(pb['BossName']), players, pb['Time'], pb['Proof'], calculateScale(pb['Players']))
            pbDatabase.append(pbToAdd)
    
    # Turn mm:ss strings into datetime
    for pb in pbDatabase:
        if ":" in pb.getTime():
            # If no :, assume already converted to seconds
            m,s = pb.getTime().split(':')
            #Convert to seconds for sorting later on
            pb.setTime(datetime.timedelta(minutes=int(m),seconds=int(s)).total_seconds())
        pb.setDiaryLevel(getDiaryLevel(pb))
        pb.setDiaryPoints(calcDiaryPoints(pb.getDiaryLevel()))

# update pb leaderboards channel
async def update_pbs():
    get_db()
    guild = get(bot.guilds, id = SERVER_ID)

    # sort into individual PersonalBestCategory objects for pb hiscores, this will not add ex clan member pbs
    for pb in pbDatabase:        
        for pbCategory in pbCategories:
            if pb.getBossName() == pbCategory.getBossName():
                if pb.getScale() == pbCategory.getScale():
                    allMembersFound = True
                    for player in pb.getPlayers().split(","):
                        try:
                            individualMemberFound = False
                            member = guild.get_member(int(player))
                            if player != str(NON_CLANNIE_UID):
                                for role in member.roles:
                                    if str(role.id) in MEMBERS_ROLES:
                                        individualMemberFound = True
                                if not individualMemberFound:
                                    allMembersFound = False
                            else:
                                allMembersFound = False
                            
                            pbAdded = False
                            for profile in pbProfiles:
                                if profile.getMember() == member.display_name:
                                    for profilePb in profile.getPbList():
                                        if profilePb.getBossName() == pb.getBossName() and profilePb.getScale() == pb.getScale():
                                            pbAdded = True
                                            if profilePb.getTime() > pb.getTime():
                                                profile.removePb(profilePb)
                                                profile.addPb(pb)
                                    if not pbAdded:
                                        profile.addPb(pb)
                                        pbAdded = True
                            if not pbAdded:
                                if member.id != int(NON_CLANNIE_UID) and individualMemberFound:
                                    profile = PersonalBestProfile(member.display_name)
                                    profile.addPb(pb)
                                    pbProfiles.append(profile)         
                        except:
                            #Non sanity member as not in discord (uid lookup failed)
                            allMembersFound = False

                    if allMembersFound:
                        existingPbFound = False
                        for personalBest in pbCategory.getPbList():
                            if personalBest.getPlayers() == pb.getPlayers():
                                existingPbFound = True
                                if personalBest.getTime() > pb.getTime():
                                    pbCategory.removePb(personalBest)
                                    pbCategory.addPb(pb)
                                    break
                        if not existingPbFound:
                            pbCategory.addPb(pb)

    for pbCategory in pbCategories:
        pbCategory.sort()
        for top3pb in top3Pbs:
            for i in range(3):
                if len(pbCategory.getPbList()) > i:
                    if top3pb.getBossName() == pbCategory.getBossName():
                        if top3pb.getScale() == pbCategory.getScale():
                            if top3pb.getPbList()[i] != pbCategory.getPbList()[i]:
                                pbsRequireUpdate[0] = True
                                top3pb.getPbList()[i] = pbCategory.getPbList()[i]
                elif top3pb.getPbList()[i] != None:
                    top3pb.getPbList()[i] = None
                    pbsRequireUpdate[0] = True
    
    if pbsRequireUpdate[0]:
        await refreshPbChannel()


async def refreshPbChannel():
    lastRefresh[0] = datetime.datetime.now() + datetime.timedelta(minutes = 5)
    guild = get(bot.guilds, id = SERVER_ID)
    pb_leaderboard = get(guild.channels, id = PB_LEADERBOARD_ID)
    await pb_leaderboard.purge(limit = 200)
    # PBs building in discord
    for category in top3Pbs:
        if top3Pbs.index(category) == 0:
            await pb_leaderboard.send(file=discord.File('resources/banners/cm.png'))
        elif top3Pbs.index(category) == 3:
            await pb_leaderboard.send(file=discord.File('resources/banners/tob.png'))
        elif top3Pbs.index(category) == 7:
            await pb_leaderboard.send(file=discord.File('resources/banners/inferno.png'))
        elif top3Pbs.index(category) == 8:
            await pb_leaderboard.send(file=discord.File('resources/banners/fight_caves.png'))
        elif top3Pbs.index(category) == 10:
            await pb_leaderboard.send(file=discord.File('resources/banners/c_gauntlet.png'))
        elif top3Pbs.index(category) == 11:
            await pb_leaderboard.send(file=discord.File('resources/banners/toa.png'))

        if top3Pbs.index(category) != 13:
            await addPbToChannel(category, pb_leaderboard, category.getScale())


    pbsRequireUpdate[0] = False

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
        try:
            member = guild.get_member(int(players))
        except:
                print("[WARNING] Id thrown when trying to find disord member: " + str(int(players)))
        return member.display_name

    return ", ".join(playerNicks)

# Add pb to channel
async def addPbToChannel(category, channel, scale):
    emoji = discord.utils.get(bot.emojis, name='bullet')
    scaleCount = 0
    scaleString = ""
    for pbCateogry in pbCategories:
        if pbCateogry.getBossName() == category.getBossName():
            scaleCount += 1
    
    if scaleCount > 1:
        scaleString = str(scale.value)
    else:
        scaleString = str(category.getBossName().value)
        
    message = (str(emoji) + " **" + scaleString + "**")
    positions = ["1st", "2nd", "3rd"]
    if len(category.getPbList()) > 0:
        message += "```yaml"
        proof = ""
        for pb in category.getPbList():
            if pb is not None:
                message += "\n" + positions[category.getPbList().index(pb)] + ": " + str(convertTime(pb.getTime())) + " - " + str(await convertPlayers(pb.getPlayers()))
                proof += "\n<" + str(pb.getProof()).strip() + "\>"
        if (proof != ""):
            message += "```"
            message += proof
        await channel.send(message)
    else:
        await channel.send("*No PBs found for category*")

async def deleteMessage(message):
    try:
        await message.delete()
    except:
        pass

async def getName(ctx, arg):
    if arg == "":
        return ctx.author.display_name
    elif '@' in arg:
        guild = get(bot.guilds, id = SERVER_ID)
        userId = int(''.join(filter(str.isdigit, arg)))
        user = guild.get_member(int(userId))
        return user.display_name
    else:
        return arg
    
    


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

def calculateScale(string):
    if string.count(",") == 0:
        return PersonalBestScale.SOLO
    elif string.count(",") == 1:
        return PersonalBestScale.DUO
    elif string.count(",") == 2:
        return PersonalBestScale.TRIO
    elif string.count(",") == 3:
        return PersonalBestScale.FOUR_MAN
    elif string.count(",") == 4:
        return PersonalBestScale.FIVE_MAN
    else: 
        return PersonalBestScale.UNKNOWN

def convertToPersonalBestBossName(bossName):
    pbBossesName = []
    pbBossesValue = []
    for boss in PersonalBestBossName:
        pbBossesName.append(boss)
        pbBossesValue.append(boss.value)

    return pbBossesName[pbBossesValue.index(difflib.get_close_matches(bossName, pbBossesValue, n = 3, cutoff = 0.01)[0])]

def calcDiaryPoints(diaryLevel):
    if diaryLevel == PersonalBestDiaryLevel.NONE:
        return 0
    elif diaryLevel == PersonalBestDiaryLevel.EASY:
        return 1
    elif diaryLevel == PersonalBestDiaryLevel.MEDIUM:
        return 3
    elif diaryLevel == PersonalBestDiaryLevel.HARD:
        return 6
    elif diaryLevel == PersonalBestDiaryLevel.ELITE:
        return 10
    elif diaryLevel == PersonalBestDiaryLevel.MASTER:
        return 15

def getDiaryLevel(pb):
    timeIndex = -1
    for category in diaryTimes:
        categoryName = pb.getBossName().value + " " + pb.getScale().value
        if categoryName == category:
            index = 0
            for time in diaryTimes[category]:
                if int(pb.getTime()) <= int(time):
                    timeIndex = index
                index += 1

    if timeIndex == 0:
        return PersonalBestDiaryLevel.EASY
    elif timeIndex == 1:
        return PersonalBestDiaryLevel.MEDIUM
    elif timeIndex == 2:
        return PersonalBestDiaryLevel.HARD
    elif timeIndex == 3:
        return PersonalBestDiaryLevel.ELITE
    elif timeIndex == 4:
        return PersonalBestDiaryLevel.MASTER
    elif timeIndex == -1:
        return PersonalBestDiaryLevel.NONE

bot.run(TOKEN)