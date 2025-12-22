/**************************************************************************
*
*	FILENAME				:	globals.h
*
*	DESCRIPTION			:	Global Values for speech channel coding and decoding
*
**************************************************************************/

#ifndef MAX_SpFrms_per_TDMFrm
  #define MAX_SpFrms_per_TDMFrm 3
#endif

int	CoderType;	/* 0 = default TETRA       */
			/* 1 = AMR 4750 bit/s MODE */

int	SpFrms_per_TDMFrm;

int	N0;
int	N1;
int	N2;
int	N0_2;
int	N1_2;
int	N2_2;
int	N1_2_coded;
int	N2_2_coded;


int	Length_vocoder_frame;
int	Length_2_frames;

int	SIZE_TAB_CRC1;
int	SIZE_TAB_CRC2;
int	SIZE_TAB_CRC3;
int	SIZE_TAB_CRC4;
int	SIZE_TAB_CRC5;
int	SIZE_TAB_CRC6;
int	SIZE_TAB_CRC7;
int	SIZE_TAB_CRC8;


int     Fs_SpFrms_per_TDMFrm;

int     Fs_N0[MAX_SpFrms_per_TDMFrm];
int     Fs_N1[MAX_SpFrms_per_TDMFrm];
int     Fs_N2[MAX_SpFrms_per_TDMFrm];

int     Fs_N0_Tot;
int     Fs_N1_Tot;
int     Fs_N2_Tot;
int     Fs_N1_Tot_coded;
int     Fs_N2_Tot_coded;

int     Fs_SIZE_TAB_CRC1;
int	Fs_SIZE_TAB_CRC2;
int	Fs_SIZE_TAB_CRC3;
int     Fs_SIZE_TAB_CRC4;

int     Fs_Fixed_Bits[MAX_SpFrms_per_TDMFrm];

