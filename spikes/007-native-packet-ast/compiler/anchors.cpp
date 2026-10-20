#include <config/core.hpp>
#include <map/packets.hpp>
#include <common/packets.hpp>
#include <cstdio>
static_assert(PACKETVER_MAIN_NUM==20180704);
#if defined(RENEWAL) || defined(PACKETVER_RE) || defined(PACKETVER_ZERO) || defined(PACKET_OBFUSCATION)
#error unexpected profile
#endif
int main(){std::printf("emotion=%zu stopmove=%zu\n", sizeof(PACKET_ZC_EMOTION),sizeof(PACKET_ZC_STOPMOVE));}
