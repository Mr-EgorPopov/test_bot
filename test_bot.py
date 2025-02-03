#include "gamethread.h"

bool GameThread::enterWorld_ = false;

bool GameThread::enterWorld ()
{
	return enterWorld_;
}

GameThread::GameThread ()
{
	tradeUi_ = 0;
}

GameThread::~GameThread ()
{
	delete teleportTimer_;
	delete pSocket_;
}

void GameThread::run ()
{
	pSocket_ = new QTcpSocket;
	teleportTimer_ = new QTimer;
	connect (teleportTimer_, SIGNAL (timeout ()), SLOT (slotTeleportTimer ()));
	connect (pSocket_, SIGNAL (readyRead ()), SLOT (slotReadyRead_ ()));
	connect (pSocket_, SIGNAL (disconnected ()), SLOT (slotDisconnected_ ()));
	connect (pSocket_, SIGNAL (connected ()), SLOT (slotConnected_ ()));
	pSocket_->connectToHost (LoginData::ip.c_str (), LoginData::port);	
	this->exec ();
}

void GameThread::slotDisconnected_ ()
{
	delete pSocket_;
	this->quit ();
}

void GameThread::slotReadyRead_ ()
{
	if (!bSize_ && pSocket_->bytesAvailable () >= 2)
	{
		QByteArray size = pSocket_->read (2);
		bSize_ = static_cast <int> (static_cast <unsigned char> (size.at (0))) + static_cast <int> (static_cast <unsigned char> (size.at (1))) * 0x100 - 2;
	}
	if (bSize_ > 0 && pSocket_->bytesAvailable () >= bSize_)
	{
		QByteArray data = pSocket_->read (bSize_);
		bSize_ = 0;
		string pck;
		for (int i = 0; i < data.size (); ++i)
		{
			pck += data.at (i);
		}
		if (init_)
		{
			pck = GameCrypt::decrypt (pck);
		}
		unsigned char packetId = static_cast <unsigned char> (pck[0]);
		if (packetId == E_S_GAME_KEY)
		{
			GameCrypt::init (pck.substr (2, 8));
			init_ = true;
			write_ (GameCrypt::encrypt (GamePacket::authRequest (LoginData::login, LoginData::key2)));
		}
		else if (packetId == E_S_GAME_CHAR_SELECT)
		{			
			vector <CharSelectItem> chars;
			GameF::charSelect (pck, &chars);
			saveGameCharSelect_ = pck;
			SelectCharDialog * ui = new SelectCharDialog (chars);
			int selection = 0;
			if (ui->exec () == QDialog::Accepted)
			{
				selection = ui->selection ();
				delete ui;
			}
			else
			{
				pSocket_->close ();
				delete ui;
				return;
			}
			if (selection == -1)
			{
				write_ (GameCrypt::encrypt (GamePacket::newCharacter ()));
			}
			else
			{
				write_ (GameCrypt::encrypt (GamePacket::charSelected (selection)));
			}
		}
		else if (packetId == E_S_GAME_QUEST_LIST)
		{
			if (!enterWorld_)
			{			
				QTimer * enterWorldTimer = new QTimer;
				enterWorldTimer->setSingleShot (true);
				connect (enterWorldTimer, SIGNAL (timeout ()), SLOT (slotEnterWorld_ ()));
				enterWorldTimer->start (3000);
			}
		}
		else if (packetId == E_S_GAME_NET_PING)
		{
			write_ (GameCrypt::encrypt (GamePacket::netPing (pck.substr (1, pck.length ()))));
		}
		else if (packetId == E_S_GAME_SSQ_INFO)
		{
			if (!enterWorld_)
			{										
				write_ (GameCrypt::encrypt (GamePacket::requestManorList ()));
			}
		}
		else if (packetId == E_S_GAME_RCVD_MANOR_LIST)
		{
			if (!enterWorld_)
			{				
				write_ (GameCrypt::encrypt (GamePacket::requestQuestList ()));
			}			
		}
		else if (packetId == E_S_GAME_NPCINFO)
		{
			emit signalCreateNpc (GameF::npcInfo (pck));
		}
		else if (packetId == E_S_GAME_CHARINFO)
		{
			emit signalCreateChar (GameF::charInfo (pck));
		}
		else if (packetId == E_S_GAME_USERINFO)
		{
			emit signalCreateUser (GameF::userInfo (pck));
		}
		else if (packetId == E_S_GAME_DELETE_OBJECT)
		{
			emit signalDeleteObject (GameF::deleteObject (pck));
		}
		else if (packetId == E_S_GAME_MOVE_TO_LOCATION)
		{
			int objId;
			CatXPoint from;
			CatXPoint to;
			Debug::write (pck);
			GameF::moveToLocation (pck, &objId, &from, &to);
			MapScene::moveToLocation (objId, from, to);
		}
		else if (packetId == E_S_GAME_MOVE_TO_PAWN)
		{
			int objId;
			int target;
			int dist;
			CatXPoint to;
			Debug::write (pck);
			GameF::moveToPawn (pck, &objId, &target, &to, &dist);
			MapScene::moveToPawn (objId, target, to, dist);
		}
		else if (packetId == E_S_GAME_NPC_HTML_MESSAGE)
		{
			NpcHtmlMessage * ui = new NpcHtmlMessage (GameF::npcHtmlMessage (pck));
			if (ui->exec () == QDialog::Accepted)
			{
				string result = ui->result ();
				for (unsigned int i = 0; i < result.length (); ++i)
				{
					result[i] = tolower (result[i]);
				}
				if (result.substr (0, 4) == "link")
				{
					write_(GameCrypt::encrypt (GamePacket::requestLinkHtml (DataFunc::encodeTo (result.substr (5, result.length ())))));
				}
				else if (result.substr (0, 9) == "bypass -h")
				{
					write_(GameCrypt::encrypt (GamePacket::requestBypassToServer (DataFunc::encodeTo (result.substr (10, result.length ())))));
				}
				else if (result.substr (0, 6) == "bypass")
				{
					write_(GameCrypt::encrypt (GamePacket::requestBypassToServer (DataFunc::encodeTo (result.substr (7, result.length ())))));					
				}
			}
			delete ui;
		}
		else if (packetId == E_S_GAME_STOP_MOVE)
		{
			CatXPoint pos;
			int objectId;
			GameF::stopMove (pck, &objectId, &pos);
			MapScene::stopMove (objectId, pos);
		}
		else if (packetId == E_S_GAME_ACTION_FAIL)
		{
			MapScene::actionFail ();
		}
		else if (packetId == E_S_GAME_PRIVATE_STORE_MANAGE_LIST)
		{
			int playerObjId;
			int packSell;
			int adena;
			vector <SellItem> items;
			GameF::privateStoreManageList (pck, &playerObjId, &packSell, &adena, &items);
			PrivateStoreManageList * ui = new PrivateStoreManageList (packSell, adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				if (ui->packet ().length ())
				{
					if (Data::sellWidget ()->motd ().length ())
					{
						write_ (GameCrypt::encrypt (GamePacket::setPrivateStoreMsg (DataFunc::encodeTo (Data::sellWidget ()->motd ()))));
					}
					write_ (GameCrypt::encrypt (GamePacket::setPrivateStoreListSell (ui->packet ())));
				}
				else
				{
					write_ (GameCrypt::encrypt (GamePacket::requestPrivateStoreQuit ()));
				}
			}
			else
			{
				write_ (GameCrypt::encrypt (GamePacket::requestPrivateStoreQuit ()));
			}
		}
		else if (packetId == E_S_GAME_PRIVATE_STORE_BUY_MANAGE_LIST)
		{
			int playerObjId;
			int adena;
			vector <BuyItem> items;
			GameF::privateStoreBuyManageList (pck, &playerObjId, &adena, &items);
			PrivateStoreManageBuyList * ui = new PrivateStoreManageBuyList (adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				if (ui->packet ().length ())
				{
					if (Data::buyWidget ()->motd ().length ())
					{
						write_ (GameCrypt::encrypt (GamePacket::setPrivateStoreMsgBuy (DataFunc::encodeTo (Data::buyWidget ()->motd ()))));
					}
					write_ (GameCrypt::encrypt (GamePacket::setPrivateStoreListBuy (ui->packet ())));
				}
				else
				{
					write_ (GameCrypt::encrypt (GamePacket::requestPrivateStoreQuitBuy ()));
				}
			}
			else
			{
				write_ (GameCrypt::encrypt (GamePacket::requestPrivateStoreQuitBuy ()));
			}
		}
		else if (packetId == E_S_GAME_PRIVATE_STORE_LIST)
		{
			int playerObjId;
			int packSell;
			int adena;
			vector <PlayerSellItem> items;
			GameF::privateStoreList (pck, &playerObjId, &packSell, &adena, &items);
			PlayerStoreList * ui = new PlayerStoreList (packSell, adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				write_ (GameCrypt::encrypt (GamePacket::sendPrivateStoreBuyList (playerObjId, ui->packet ())));
			}
			delete ui;
		}
		else if (packetId == E_S_GAME_PRIVATE_BUY_LIST_BUY)
		{
			int playerObjId;
			int adena;
			vector <PlayerBuyItem> items;
			GameF::privateBuyListBuy (pck, &playerObjId, &adena, &items);
			PlayerStoreListBuy * ui = new PlayerStoreListBuy (adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				write_ (GameCrypt::encrypt (GamePacket::sendPrivateStoreBuyListBuy (playerObjId, ui->packet ())));
			}
			delete ui;			
		}
		else if (packetId == E_S_GAME_TRADE_REQUEST)
		{
			int senderId;
			GameF::tradeRequest (pck, &senderId);
			string name;
			for (unsigned int i = 0; i < MapScene::vChar.size (); ++i)
			{
				if (MapScene::vChar[i].objectId () == senderId)
				{
					name = MapScene::vChar[i].name ();
					break;
				}
			}
			TradeRequest * ui = new TradeRequest (name);
			if (ui->exec () == QDialog::Accepted)
			{
				write_ (GameCrypt::encrypt (GamePacket::answerTradeRequest (1)));
			}
			else
			{
				write_ (GameCrypt::encrypt (GamePacket::answerTradeRequest (0)));
			}
			delete ui;
		}
		else if (packetId == E_S_GAME_TRADE_START)
		{
			int objectId;
			vector <TradeItem> items;
			string name;
			GameF::tradeStart (pck, &objectId, &items);
			for (unsigned int i = 0; i < MapScene::vChar.size (); ++i)
			{
				if (MapScene::vChar[i].objectId () == objectId)
				{
					name = MapScene::vChar[i].name ();
					break;
				}
			}
			if (tradeUi_)
			{
				delete tradeUi_;
			}
			tradeUi_ = new Trade (name, objectId, items);
			connect (tradeUi_, SIGNAL (sendPacket (const string &)), SLOT (slotMap (const string &)));
			if (tradeUi_->exec () == QDialog::Rejected)
			{
				tradeUi_->slotCancel ();
			}
		}
		else if (packetId == E_S_GAME_TRADE_OWN_ADD)
		{
			vector <TradeItem> items;
			GameF::tradeOwnAdd (pck, &items);
			tradeUi_->tradeOwnAdd (items);
		}
		else if (packetId == E_S_GAME_TRADE_OTHER_ADD)
		{
			vector <TradeItem> items;
			GameF::tradeOwnAdd (pck, &items);
			tradeUi_->tradeOtherAdd (items);
		}
		else if (packetId == E_S_GAME_TRADE_DONE)
		{
			if (tradeUi_)
			{
				tradeUi_->reject ();
			}
		}
		else if (packetId == E_S_GAME_TRADE_PRESS_OWN_OK)
		{
			tradeUi_->tradePressOwnOk ();
		}
		else if (packetId == E_S_GAME_TRADE_PRESS_OTHER_OK)
		{
			tradeUi_->tradePressOtherOk ();
		}
		else if (packetId == E_S_GAME_TRADE_PRESS_OWN_OK)
		{
			tradeUi_->tradePressOwnOk ();
		}
		else if (packetId == E_S_GAME_BUY_LIST)
		{
			int adena;
			int saleId;
			vector <NpcSellItem> items;
			GameF::buyList (pck, &adena, &saleId, &items);
			NpcTradeSell * ui = new NpcTradeSell (adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				write_ (GameCrypt::encrypt (GamePacket::requestBuyItem (saleId, ui->packet ())));
			}
			delete ui;
		}
		else if (packetId == E_S_GAME_SELL_LIST)
		{
			int adena;
			int saleId;
			vector <NpcBuyItem> items;
			GameF::sellList (pck, &adena, &saleId, &items);
			NpcTradeBuy * ui = new NpcTradeBuy (adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				write_ (GameCrypt::encrypt (GamePacket::requestSellItem (saleId, ui->packet ())));
			}
			delete ui;
		}
		else if (packetId == E_S_GAME_WAREHOUSE_DEPOSIT_LIST)
		{
			int adena;
			int whtype;
			vector <WarehouseItem> items;
			GameF::wareHouseDepositList (pck, &whtype, &adena, &items);
			WarehouseDeposit * ui = new WarehouseDeposit (adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				write_ (GameCrypt::encrypt (GamePacket::sendWareHouseDepositList (ui->packet ())));
			}
			delete ui;
		}
		else if (packetId == E_S_GAME_WAREHOUSE_WITHDRAW_LIST)
		{
			int adena;
			int whtype;
			vector <WarehouseItem> items;
			GameF::wareHouseDepositList (pck, &whtype, &adena, &items);
			WarehouseWithdraw * ui = new WarehouseWithdraw (adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				write_ (GameCrypt::encrypt (GamePacket::sendWareHouseWithdrawList (ui->packet ())));
			}
			delete ui;			
		}
		else if (packetId == E_S_GAME_PRIVATE_STORE_MSG)
		{
			int objectId;
			string msg;
			GameF::privateStoreMsg (pck, &objectId, &msg);
			if (MapScene::user.objectId () != objectId)
			{
				emit signalAddItem (objectId, E_INFO_SELL, msg);
				MapScene::setAlt (objectId, msg);
			}
		}
		else if (packetId == E_S_GAME_RECIPE_SHOP_MSG)
		{
			int objectId;
			string msg;
			GameF::privateStoreMsg (pck, &objectId, &msg);
			if (MapScene::user.objectId () != objectId)
			{
				emit signalAddItem (objectId, E_INFO_CRAFT, msg);
				MapScene::setAlt (objectId, msg);
			}
		}
		else if (packetId == E_S_GAME_CHANGE_WAIT_TYPE)
		{
			int objectId;
			int waitType;
			CatXPoint pos;
			GameF::changeWaitType (pck, &objectId, &waitType, &pos);
			if (objectId == MapScene::user.objectId ())
			{
				if (waitType == 0)
				{
					MapScene::setWaitType (0);
					write_ (GameCrypt::encrypt (GamePacket::requestActionUse (0)));
				}
				else
				{
					MapScene::setWaitType (1);
				}
			}
			else
			{
				emit signalDeleteItem (objectId, E_INFO_SELL);
				emit signalDeleteItem (objectId, E_INFO_BUY);
				emit signalDeleteItem (objectId, E_INFO_CRAFT);
				MapScene::setAlt (objectId, "");
			}
		}
		else if (packetId == E_S_GAME_RECIPE_SHOP_MANAGE_LIST)
		{
			int objectId;
			int adena;
			int isDwarfen;
			vector <DwarfenManufactureItem> recipe;
			vector <DwarfenManufactureItem> list;
			GameF::recipeShopManageList (pck, &objectId, &adena, &isDwarfen, &recipe, &list);
			DwarfenManufacture * ui = new DwarfenManufacture (recipe, list);
			if (ui->exec () == QDialog::Accepted)
			{
				if (ui->message ().length ())
				{
					write_ (GameCrypt::encrypt (GamePacket::requestRecipeShopMessageSet (DataFunc::encodeTo (ui->message ()))));
				}
				write_ (GameCrypt::encrypt (GamePacket::requestRecipeShopListSet (ui->packet ())));
			}
			delete ui;
		}
		else if (packetId == E_S_GAME_SAY2)
		{
			int objectId;
			int type;
			string player;
			string msg;
			GameF::say2 (pck, &objectId, &type, &player, &msg);
			player = DataFunc::encodeFrom (player);
			msg = DataFunc::encodeFrom (msg);
			emit signalSay2 (DataFunc::intToString (type) + player + static_cast <char> (0) + msg);
		}
		else if (packetId == E_S_GAME_SYSTEM_MESSAGE)
		{
			int msgId;
			vector <SystemItem> items;
			GameF::systemMessage (pck, &msgId, &items);
			emit signalSystemMessage (Data::buildSystemMessage (msgId, items));
		}
		else if (packetId == E_S_GAME_GM_HIDE)
		{
			int id;
			GameF::gmHide (pck, &id);
			write_ (GameCrypt::encrypt (GamePacket::appearing ()));
		}
		else if (packetId == E_S_GAME_ITEM_LIST_PACKET)
		{
			int window;
			vector <InventoryItem> items;
			GameF::itemListPacket (pck, &window, &items);
			emit signalItemList (items);
		}
		else if (packetId == E_S_GAME_INVENTORY_UPDATE)
		{
			vector <InventoryItem> items;
			GameF::inventoryUpdate (pck, &items);
			emit signalItemList (items);
		}
		else if (packetId == E_S_GAME_TELEPORT_TO_LOCATION)
		{
			int objectId;
			CatXPoint pos;
			GameF::teleportToLocation (pck, &objectId, &pos);
			MapScene::teleportToLocation (objectId, pos);
			teleportTimer_->start (5000);
		}
		else if (packetId == E_S_GAME_RESTART_RESPONSE)
		{
			int ok;
			string msg;
			GameF::restartResponse (pck, &ok, &msg);
			if (ok)
			{
				emit signalDeleteObject (MapScene::user.objectId ());
				enterWorld_ = false;
				emit enterWorld (false);
			}
		}
		else if (packetId == E_S_GAME_LOGOUT_OK)
		{
			for (unsigned int i = 0; i < MapScene::vChar.size (); ++i)
			{
				emit signalDeleteObject (MapScene::vChar[0].objectId ());				
			}
			for (unsigned int i = 0; i < MapScene::vNpc.size (); ++i)
			{
				emit signalDeleteObject (MapScene::vNpc[0].objectId ());				
			}
			emit signalDeleteObject (MapScene::user.objectId ());
			enterWorld_ = false;
			emit enterWorld (false);
			pSocket_->close ();
		}
		else if (packetId == E_S_GAME_CHAR_TEMPLATES)
		{
			vector <CharTemplate> chars;
			GameF::charTemplates (pck, &chars);
			NewChar * di = new NewChar (chars);
			if (di->exec () == QDialog::Accepted)
			{
				for (unsigned int i = 0; i < chars.size (); ++i)
				{
					if (chars[i].classId == di->classId ())
					{
						write_ (GameCrypt::encrypt (GamePacket::charCreate (DataFunc::encodeTo (di->name ()), di->sex (), chars[i], di->style (), di->hair (), di->face ())));
						break;
					}
				}
				delete di;
			}
			else
			{
				delete di;
				pck = saveGameCharSelect_;
				vector <CharSelectItem> chars;
				GameF::charSelect (pck, &chars);
				saveGameCharSelect_ = pck;
				SelectCharDialog * ui = new SelectCharDialog (chars);
				int selection = 0;
				if (ui->exec () == QDialog::Accepted)
				{
					selection = ui->selection ();
					delete ui;
				}
				else
				{
					pSocket_->close ();
					delete ui;
					return;
				}
				if (selection == -1)
				{
					write_ (GameCrypt::encrypt (GamePacket::newCharacter ()));
				}
				else
				{
					write_ (GameCrypt::encrypt (GamePacket::charSelected (selection)));
				}
			}
		}
		else if (packetId == E_S_GAME_CHAR_CREATE_FAIL)
		{
			ErrorDialog * nya = new ErrorDialog ("Char with this name exists");
			nya->exec ();
			delete nya;
			pck = saveGameCharSelect_;
			vector <CharSelectItem> chars;
			GameF::charSelect (pck, &chars);
			saveGameCharSelect_ = pck;
			SelectCharDialog * ui = new SelectCharDialog (chars);
			int selection = 0;
			if (ui->exec () == QDialog::Accepted)
			{
				selection = ui->selection ();
				delete ui;
			}
			else
			{
				pSocket_->close ();
				delete ui;
				return;
			}
			if (selection == -1)
			{
				write_ (GameCrypt::encrypt (GamePacket::newCharacter ()));
			}
			else
			{
				write_ (GameCrypt::encrypt (GamePacket::charSelected (selection)));
			}
		}
		else if (packetId == E_S_GAME_RECIPE_SHOP_SELL_LIST)
		{
			vector <RecipeShopItem> items;
			int objectId;
			int mp;
			int maxMp;
			int adena;
			GameF::recipeShopSellList (pck, &objectId, &mp, &maxMp, &adena, &items);
			RecipeShopSellList * ui = new RecipeShopSellList (mp, maxMp, adena, items);
			if (ui->exec () == QDialog::Accepted)
			{
				write_ (GameCrypt::encrypt (GamePacket::requestRecipeShopMakeInfo (objectId, items [ui->rowId ()].recipeId)));
			}
			delete ui;
		}
		else if (packetId == E_S_GAME_RECIPE_SHOP_ITEM_INFO)
		{
			int shopId;
			int recipeId;
			int mp;
			int maxMp;
			GameF::recipeShopItemInfo (pck, &shopId, &recipeId, &mp, &maxMp);
			RecipeShopItemInfo * ui = new RecipeShopItemInfo (recipeId, mp, maxMp);
			if (ui->exec () == QDialog::Accepted)
			{
				if (ui->selection () == 0)
				{
					//craft 
					delete ui;
					write_ (GameCrypt::encrypt (GamePacket::requestRecipeShopMakeItem (shopId, recipeId)));
				}
				else if (ui->selection () == 1)
				{
					// prev
					delete ui;
					write_ (GameCrypt::encrypt (GamePacket::requestRecipeShopPrev (shopId)));
				}
			}
			else
			{
				delete ui;
			}
		}
		else if (packetId == E_S_GAME_SOCIAL_ACTION)
		{
		}
		else if (packetId == E_S_GAME_FINISH_ROTATING)
		{
		}
		else
		{
			Debug::write (pck);
		}
		slotReadyRead_ ();		
	}
}

void GameThread::slotConnected_ ()
{
	bSize_ = 0;
	init_ = false;
	enterWorld_ = false;
	write_ (GamePacket::protocolVersion (REVISION));
}

void GameThread::write_ (const string & str) const
{
	string pck;
	unsigned int len = str.length () + 2;
	pck += len % 0x100;
	pck += len / 0x100;
	pck += str;
	pSocket_->write (pck.c_str (), pck.length ());
}

void GameThread::slotEnterWorld_ ()
{
	write_ (GameCrypt::encrypt (GamePacket::enterWorld ()));
	write_ (GameCrypt::encrypt (GamePacket::requestItemList ()));
	enterWorld_ = true;
	emit enterWorld (true);
}

void GameThread::slotMap (const string & pck)
{
	if (enterWorld_)
	{
			write_ (GameCrypt::encrypt (pck));
	}
}

void GameThread::slotSell_ (bool)
{
	write_ (GameCrypt::encrypt (GamePacket::requestPrivateStoreManage ()));
}

void GameThread::slotBuy_ (bool)
{
	write_ (GameCrypt::encrypt (GamePacket::requestPrivateStoreManageBuy ()));
}

void GameThread::slotDwarfenManufacture_ (bool)
{
	write_ (GameCrypt::encrypt (GamePacket::requestActionUse (E_ACTION_DWARFEN_MANUFACTURE)));
}

void GameThread::slotSay2 (const string & msg, const int type, const string & pm)
{
	if (enterWorld_)
	{
		if (msg.substr (0, 2) == "//")
		{
			write_ (GameCrypt::encrypt (GamePacket::sendBypassBuildCmd (DataFunc::encodeTo (msg.substr (2, msg.length ())))));
		}
		else
		{
			if (pm.length ())
			{
				write_ (GameCrypt::encrypt (GamePacket::say2 (DataFunc::encodeTo (msg), type, DataFunc::encodeTo (pm))));
			}
			else
			{
				write_ (GameCrypt::encrypt (GamePacket::say2 (DataFunc::encodeTo (msg), type)));
			}
		}
	}
}

void GameThread::slotTeleportTimer ()
{
	teleportTimer_->stop ();
	write_ (GameCrypt::encrypt (GamePacket::appearing ()));
}

void GameThread::slotRestart (bool)
{
	write_ (GameCrypt::encrypt (GamePacket::requestRestart ()));
}

void GameThread::slotLogout (bool)
{
	write_ (GameCrypt::encrypt (GamePacket::requestLogout ()));
}

